"""
WAF events into the SIEM (#1169): provision and tear down event forwarding.

What "Set up event forwarding" creates, and why each piece is shaped as it is:

- **A Syslog TCP input per WAF** (no TLS), on its own port from ``WAF_SYSLOG_PORT_RANGE``.
  One input per WAF is what gives every message a clean identity: the WAF's payload
  names neither customer nor WAF, so the input's **static fields** add them —
  ``syslog_type=waf`` and ``syslog_customer=<code>``, the exact fields CoPilot's alert
  pipeline already reads for the source and the customer (Fortinet uses the same
  pair), plus ``waf_name``.
- **Two extractors** on that input. The forwarder sends ``<transaction_id> - {json}``:
  a regex extractor copies the JSON into ``waf_json``, then a JSON extractor flattens
  it with the **``waf_`` prefix**. The prefix is load-bearing: unprefixed, the payload's
  ``timestamp`` and ``source`` overwrite Graylog's own fields — the timestamp fails to
  parse (``gl2_processing_error``) and the real syslog source is lost. Prefixed, the
  event time comes from the syslog header as it should.
- **A ``waf-<code>`` index set and a stream per customer**, shared by the customer's
  WAFs: 30-day retention (daily rotation, 30 indices), 1 shard. The stream matches the
  static fields, so it never depends on the extractors having run.
- **A syslog forwarder on the WAF** pointing at the input, then the WAF's own test.

Every externally visible step registers an undo; a failure unwinds newest-first so a
run either completes or leaves nothing behind (the same discipline as Office365
provisioning). Objects that were *reused* — a sibling WAF's stream and index set — are
never undone.

The syslog destination is explicit (``syslog_host``) because it is what the *WAF* can
reach, which is often not the address CoPilot uses for Graylog's API.
"""

import os
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Awaitable
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.connectors.graylog.utils.universal import send_delete_request
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.utils.universal import send_post_request_create_entity
from app.customer_waf.services.customer_waf import capabilities_for_roles
from app.customer_waf.utils.universal import WafRequestError
from app.customer_waf.utils.universal import waf_request
from app.db.universal_models import Customers
from app.db.universal_models import CustomerWafInstance

SYSLOG_TYPE = "waf"
WAF_SOURCE = "socfortress-waf"
SYSLOG_INPUT_TYPE = "org.graylog2.inputs.syslog.tcp.SyslogTCPInput"
DEFAULT_PORT_RANGE = "5600-5699"
RETENTION_DAYS = 30
SHARDS = 1


class ForwardingError(Exception):
    """Provisioning failed; ``status_code`` for the route, rollback already done."""

    def __init__(self, detail: str, status_code: int = 502, rollback_failures: Optional[List[str]] = None):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.rollback_failures = rollback_failures or []


# ── naming / config ────────────────────────────────────────────────────────


def input_title(row: CustomerWafInstance) -> str:
    return f"SOCFORTRESS WAF - {row.customer_code} - {row.name}"


def stream_title(customer_code: str) -> str:
    return f"SOCFORTRESS WAF - {customer_code}"


def index_prefix(customer_code: str) -> str:
    # Graylog index prefixes must be lowercase.
    return f"waf-{customer_code.lower()}"


def port_range() -> Tuple[int, int]:
    raw = (os.environ.get("WAF_SYSLOG_PORT_RANGE") or DEFAULT_PORT_RANGE).strip()
    try:
        low, high = (int(p) for p in raw.split("-", 1))
    except ValueError:
        raise ForwardingError(f"WAF_SYSLOG_PORT_RANGE must look like 5600-5699, got '{raw}'", status_code=400)
    if not (1024 <= low <= high <= 65535):
        raise ForwardingError(f"WAF_SYSLOG_PORT_RANGE '{raw}' is outside 1024-65535", status_code=400)
    return low, high


def default_syslog_host() -> Optional[str]:
    return (os.environ.get("WAF_SYSLOG_DEFAULT_HOST") or "").strip() or None


def pick_port(used: set, low: int, high: int) -> int:
    for port in range(low, high + 1):
        if port not in used:
            return port
    raise ForwardingError(f"No free port left in {low}-{high} for a new WAF input. Widen WAF_SYSLOG_PORT_RANGE.", status_code=409)


# ── Graylog payloads (shapes verified against Graylog 7.1.2's OpenAPI) ─────


def input_payload(row: CustomerWafInstance, port: int) -> dict:
    return {
        "title": input_title(row),
        "type": SYSLOG_INPUT_TYPE,
        "global": True,
        "configuration": {
            "bind_address": "0.0.0.0",
            "port": port,
            "tls_enable": False,
            "recv_buffer_size": 1048576,
            "tcp_keepalive": False,
            "use_null_delimiter": False,
            "max_message_size": 2097152,
            "force_rdns": False,
            "allow_override_date": True,
            "store_full_message": False,
            "expand_structured_data": False,
            "number_worker_threads": 2,
            "charset_name": "UTF-8",
        },
    }


def static_fields(row: CustomerWafInstance) -> List[dict]:
    return [
        {"key": "syslog_type", "value": SYSLOG_TYPE},
        {"key": "syslog_customer", "value": row.customer_code},
        {"key": "waf_name", "value": row.name},
    ]


def extractor_payloads() -> List[dict]:
    return [
        {
            "title": "WAF - pull the JSON out of the syslog message",
            "extractor_type": "regex",
            "source_field": "message",
            "target_field": "waf_json",
            "cursor_strategy": "copy",
            # Cheap guard so the regex only runs on the forwarder's events.
            "condition_type": "string",
            "condition_value": WAF_SOURCE,
            "extractor_config": {"regex_value": r"^\S+ - (\{.*\})$"},
            "converters": [],
            "order": 0,
        },
        {
            "title": "WAF - expand the JSON into waf_* fields",
            "extractor_type": "json",
            "source_field": "waf_json",
            "target_field": "",
            "cursor_strategy": "copy",
            "condition_type": "none",
            "condition_value": "",
            "extractor_config": {
                "flatten": True,
                "list_separator": ", ",
                "key_separator": "_",
                "kv_separator": "=",
                "key_prefix": "waf_",
                "replace_key_whitespace": True,
                "key_whitespace_replacement": "_",
            },
            "converters": [],
            "order": 1,
        },
        {
            # The first matched rule's message, e.g. "SQL Injection Attack Detected via
            # libinjection" — the CoPilot alert title (#1169 4b). The JSON extractor flattens
            # the matched_rules list into one string, so it can't be used as a title.
            "title": "WAF - first matched rule message",
            "extractor_type": "regex",
            "source_field": "waf_json",
            "target_field": "waf_rule_msg",
            "cursor_strategy": "copy",
            "condition_type": "string",
            "condition_value": '"matched_rules":[{',
            "extractor_config": {"regex_value": r'"matched_rules":\[\{"id":"[^"]*","msg":"((?:[^"\\]|\\.)*)"'},
            "converters": [],
            "order": 2,
        },
    ]


def index_set_payload(customer_code: str, customer_name: str) -> dict:
    return {
        "title": f"{customer_name} - WAF",
        "description": f"{customer_code} - SOCFortress WAF events",
        "index_prefix": index_prefix(customer_code),
        "rotation_strategy_class": "org.graylog2.indexer.rotation.strategies.TimeBasedRotationStrategy",
        "rotation_strategy": {
            "type": "org.graylog2.indexer.rotation.strategies.TimeBasedRotationStrategyConfig",
            "rotation_period": "P1D",
            "rotate_empty_index_set": False,
            "max_rotation_period": None,
        },
        # Daily rotation x 30 indices = 30-day retention.
        "retention_strategy_class": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategy",
        "retention_strategy": {
            "type": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategyConfig",
            "max_number_of_indices": RETENTION_DAYS,
        },
        "creation_date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "index_analyzer": "standard",
        "shards": SHARDS,
        "replicas": 0,
        "index_optimization_max_num_segments": 1,
        "index_optimization_disabled": False,
        "writable": True,
        "field_type_refresh_interval": 5000,
    }


def stream_payload(customer_code: str, index_set_id: str) -> dict:
    return {
        "title": stream_title(customer_code),
        "description": f"SOCFortress WAF events for customer {customer_code}",
        "index_set_id": index_set_id,
        # Match the input's static fields, not extracted ones: routing then never depends
        # on an extractor having run.
        "rules": [
            {"field": "syslog_type", "type": 1, "inverted": False, "value": SYSLOG_TYPE},
            {"field": "syslog_customer", "type": 1, "inverted": False, "value": customer_code},
        ],
        "matching_type": "AND",
        "remove_matches_from_default_stream": True,
        "content_pack": None,
    }


def forwarder_payload(row: CustomerWafInstance, host: str, port: int) -> dict:
    return {
        "name": f"CoPilot SIEM ({row.customer_code})",
        "type": "syslog",
        "is_enabled": True,
        "syslog_host": host,
        "syslog_port": port,
        "syslog_tls": False,
        "syslog_app_name": "waf-platform",
    }


# ── rollback ───────────────────────────────────────────────────────────────


@dataclass
class _Rollback:
    steps: List[Tuple[str, Callable[[], Awaitable[object]]]] = field(default_factory=list)

    def add(self, description: str, undo: Callable[[], Awaitable[object]]) -> None:
        self.steps.append((description, undo))

    async def run(self) -> List[str]:
        """Undo newest-first; one failing undo never abandons the rest."""
        failures = []
        for description, undo in reversed(self.steps):
            try:
                await undo()
                logger.info(f"WAF forwarding rollback: undid {description}")
            except Exception as e:  # noqa: BLE001 - keep unwinding
                failures.append(f"{description}: {e}")
                logger.error(f"WAF forwarding rollback: could not undo {description}: {e}")
        return failures


# ── lookups ────────────────────────────────────────────────────────────────


async def _used_ports() -> set:
    inputs = (await send_get_request("/api/system/inputs"))["data"].get("inputs", [])
    ports = set()
    for i in inputs:
        try:
            ports.add(int((i.get("attributes") or {}).get("port")))
        except (TypeError, ValueError):
            continue
    return ports


async def _find_index_set(customer_code: str) -> Optional[str]:
    data = (await send_get_request("/api/system/indices/index_sets", params={"skip_config_check": "true"}))["data"]
    return next((s["id"] for s in data.get("index_sets", []) if s.get("index_prefix") == index_prefix(customer_code)), None)


async def _find_stream(customer_code: str) -> Optional[str]:
    data = (await send_get_request("/api/streams"))["data"]
    return next((s["id"] for s in data.get("streams", []) if s.get("title") == stream_title(customer_code)), None)


async def _customer_name(session: AsyncSession, customer_code: str) -> str:
    customer = (await session.execute(select(Customers).where(Customers.customer_code == customer_code))).scalars().first()
    return customer.customer_name if customer else customer_code


async def _siblings_forwarding(session: AsyncSession, row: CustomerWafInstance) -> List[CustomerWafInstance]:
    result = await session.execute(
        select(CustomerWafInstance).where(
            CustomerWafInstance.customer_code == row.customer_code,
            CustomerWafInstance.id != row.id,
            CustomerWafInstance.forwarding_provisioned_at.is_not(None),
        ),
    )
    return list(result.scalars().all())


# ── provision / deprovision ────────────────────────────────────────────────


@dataclass
class ProvisionResult:
    test_success: Optional[bool]
    test_message: Optional[str]
    reused: List[str]


async def provision(session: AsyncSession, row: CustomerWafInstance, syslog_host: str) -> ProvisionResult:
    if row.forwarding_provisioned_at is not None:
        raise ForwardingError("Event forwarding is already set up for this WAF — remove it first to change it.", status_code=409)

    # Fail fast, before touching Graylog: creating the WAF forwarder needs config:write.
    me = await waf_request(row, "GET", "/users/me")
    roles = [r.get("name") for r in (me.get("roles") or []) if isinstance(r, dict)]
    if not capabilities_for_roles(roles).can_manage_forwarders:
        raise ForwardingError(
            "The WAF token's user can't create log forwarders (needs the WAF 'admin' role). "
            "Use a token for an admin user, or set up the forwarder on the WAF by hand.",
            status_code=400,
        )

    low, high = port_range()
    rollback = _Rollback()
    reused: List[str] = []
    try:
        port = pick_port(await _used_ports(), low, high)

        created = (await send_post_request("/api/system/inputs", data=input_payload(row, port)))["data"]
        input_id = created["id"]
        rollback.add(f"Graylog input {input_id}", lambda: send_delete_request(f"/api/system/inputs/{input_id}"))

        for sf in static_fields(row):
            await send_post_request(f"/api/system/inputs/{input_id}/staticfields", data=sf)
        for extractor in extractor_payloads():
            await send_post_request(f"/api/system/inputs/{input_id}/extractors", data=extractor)

        index_set_id = await _find_index_set(row.customer_code)
        if index_set_id:
            reused.append(f"index set {index_prefix(row.customer_code)}")
        else:
            name = await _customer_name(session, row.customer_code)
            index_set_id = (await send_post_request("/api/system/indices/index_sets", data=index_set_payload(row.customer_code, name)))[
                "data"
            ]["id"]
            rollback.add(
                f"Graylog index set {index_set_id}",
                lambda: send_delete_request(f"/api/system/indices/index_sets/{index_set_id}", params={"delete_indices": "true"}),
            )

        stream_id = await _find_stream(row.customer_code)
        if stream_id:
            reused.append(f"stream '{stream_title(row.customer_code)}'")
        else:
            stream_id = (await send_post_request_create_entity("/api/streams", entity=stream_payload(row.customer_code, index_set_id)))[
                "data"
            ]["stream_id"]
            rollback.add(f"Graylog stream {stream_id}", lambda: send_delete_request(f"/api/streams/{stream_id}"))
            await send_post_request(f"/api/streams/{stream_id}/resume")

        forwarder = await waf_request(row, "POST", "/forwarders/", json=forwarder_payload(row, syslog_host, port), timeout=30.0)
        forwarder_id = str(forwarder["id"])
        rollback.add(f"WAF forwarder {forwarder_id}", lambda: waf_request(row, "DELETE", f"/forwarders/{forwarder_id}"))
    except (HTTPException, WafRequestError, ForwardingError, KeyError, TypeError) as e:
        failures = await rollback.run()
        detail = getattr(e, "detail", None) or str(e)
        logger.error(f"WAF {row.id}: event forwarding provisioning failed: {detail}")
        if isinstance(e, ForwardingError):
            e.rollback_failures = failures
            raise
        raise ForwardingError(f"Setting up event forwarding failed: {detail}", rollback_failures=failures)

    row.syslog_host = syslog_host
    row.syslog_port = port
    row.graylog_input_id = input_id
    row.graylog_stream_id = stream_id
    row.graylog_index_set_id = index_set_id
    row.waf_forwarder_id = forwarder_id
    row.forwarding_provisioned_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info(f"WAF {row.id} ({row.customer_code}/{row.name}): forwarding to {syslog_host}:{port}, input {input_id}, stream {stream_id}")

    # The WAF sends a synthetic event: proves WAF → Graylog reachability end to end.
    # Reported, not fatal — a firewall to open is fixable without re-provisioning.
    try:
        test = await waf_request(row, "POST", f"/forwarders/{forwarder_id}/test", timeout=30.0)
        return ProvisionResult(bool(test.get("success")), test.get("message"), reused)
    except WafRequestError as e:
        return ProvisionResult(False, e.detail, reused)


async def deprovision(session: AsyncSession, row: CustomerWafInstance) -> List[str]:
    """Remove this WAF's forwarder and input; the customer's stream only if no sibling still forwards.

    The index set — and the WAF events already stored in it — is kept: removing
    forwarding must not delete a customer's retained data. Re-provisioning reuses it.
    Returns warnings for anything that could not be removed.
    """
    warnings: List[str] = []
    if row.waf_forwarder_id:
        try:
            await waf_request(row, "DELETE", f"/forwarders/{row.waf_forwarder_id}", allow_disabled=True)
        except WafRequestError as e:
            if e.reason != "not_found":
                warnings.append(f"Could not remove the forwarder on WAF '{row.name}' ({e.detail}). Remove it in the WAF UI.")
    if row.graylog_input_id:
        try:
            await send_delete_request(f"/api/system/inputs/{row.graylog_input_id}")
        except HTTPException as e:
            warnings.append(f"Could not remove Graylog input {row.graylog_input_id}: {e.detail}")
    if row.graylog_stream_id and not await _siblings_forwarding(session, row):
        try:
            await send_delete_request(f"/api/streams/{row.graylog_stream_id}")
        except HTTPException as e:
            warnings.append(f"Could not remove Graylog stream {row.graylog_stream_id}: {e.detail}")

    row.syslog_host = None
    row.syslog_port = None
    row.graylog_input_id = None
    row.graylog_stream_id = None
    row.graylog_index_set_id = None
    row.waf_forwarder_id = None
    row.forwarding_provisioned_at = None
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return warnings
