"""
CoPilot alerts from SOCFortress WAF events (#1169, phase 4b).

Two Monitoring Alerts catalog entries, provisioned once per Graylog (not per
customer): each event already carries its customer in ``syslog_customer`` — the
static field the forwarding input stamps (see ``forwarding.py``) and one of the
keys ``get_customer_code`` reads — so one definition serves every customer.

- **SOCFORTRESS WAF BLOCKED** — per-event. Every ``waf_action:blocked`` event
  becomes a Graylog event with ``COPILOT_ALERT_ID=NONE``; the existing collector
  (``invoke_alert_creation_collect``) turns it into an incident alert. The alert
  title is ``waf_rule_msg`` (the first matched rule's message), and ``create_alert``
  merges a new event into an *open* alert with the same title — so repeated SQLi
  blocks roll up into one alert per customer, each attacking IP added as an IoC.
- **SOCFORTRESS WAF BRUTE FORCE** — threshold. ``count() >= 30`` grouped by
  ``syslog_customer`` + ``waf_client_ip`` over 5 minutes. An aggregation event has
  no single source message, so it cannot use the per-event collector (which reads
  the event's ``origin_context``); Graylog POSTs it to
  ``/api/incidents/alerts/create/threshold`` instead, authenticated by the
  ``graylog`` header, and that route resolves a representative document from
  ``waf-*`` (the ``<source>-*`` fallback of ``threshold_index_mapping``).

Both register ``waf`` as an alert source in the incident_management_*fieldname
tables (idempotently) — without that, ``validate_syslog_type_source`` rejects the
events. The customer-code table is not written: nothing reads it (see
``add_customer_code_name``).
"""

import os
import secrets
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request_create_entity
from app.connectors.graylog.utils.universal import send_put_request
from app.customer_waf.services.forwarding import SYSLOG_TYPE
from app.db.db_session import get_db_session
from app.incidents.services.db_operations import add_alert_title_name
from app.incidents.services.db_operations import add_asset_name
from app.incidents.services.db_operations import add_field_name
from app.incidents.services.db_operations import add_ioc_name
from app.incidents.services.db_operations import add_timefield_name

BLOCKED_TITLE = "SOCFORTRESS WAF BLOCKED"
BRUTE_FORCE_TITLE = "SOCFORTRESS WAF BRUTE FORCE"
THRESHOLD_NOTIFICATION_TITLE = "SEND TO COPILOT - WAF THRESHOLD"
THRESHOLD_ROUTE = "/api/incidents/alerts/create/threshold"

BRUTE_FORCE_THRESHOLD = 30
BRUTE_FORCE_WINDOW_MS = 5 * 60 * 1000
BRUTE_FORCE_EVERY_MS = 60 * 1000

# How a WAF event maps onto a CoPilot alert (source "waf").
ALERT_FIELDS: List[str] = [
    "waf_rule_msg",
    "waf_action",
    "waf_client_ip",
    "waf_method",
    "waf_host",
    "waf_uri",
    "waf_rule_id",
    "waf_severity",
    "waf_anomaly_score",
    "waf_matched_rules",
    "waf_name",
    "waf_site_id",
    "waf_transaction_id",
]
ASSET_FIELD = "waf_host"  # the protected site, e.g. crm.example.com
TIMEFIELD = "timestamp"  # Graylog's, from the syslog header
TITLE_FIELD = "waf_rule_msg"  # e.g. "SQL Injection Attack Detected via libinjection"
IOC_FIELDS = ["waf_client_ip"]


async def ensure_waf_alert_source() -> None:
    """Register ``waf`` in the six field-mapping tables; each add_* is a no-op when the row exists."""
    async with get_db_session() as session:
        for name in ALERT_FIELDS:
            await add_field_name(SYSLOG_TYPE, name, session)
        await add_asset_name(SYSLOG_TYPE, ASSET_FIELD, session)
        await add_timefield_name(SYSLOG_TYPE, TIMEFIELD, session)
        await add_alert_title_name(SYSLOG_TYPE, TITLE_FIELD, session)
        for name in IOC_FIELDS:
            await add_ioc_name(SYSLOG_TYPE, name, session)
        await session.commit()
    logger.info("WAF alert source 'waf' registered in the incident field-mapping tables")


def _template(value: str, require: bool = True) -> dict:
    return {"data_type": "string", "providers": [{"type": "template-v1", "template": value, "require_values": require}]}


def blocked_definition(execute_every_ms: int, search_within_ms: int) -> dict:
    return {
        "title": BLOCKED_TITLE,
        "description": "A SOCFortress WAF blocked a request. Creates (or adds to) a CoPilot alert per rule and customer.",
        "priority": 2,
        "alert": True,
        "config": {
            "type": "aggregation-v1",
            "query": f"syslog_type:{SYSLOG_TYPE} AND waf_action:blocked",
            "query_parameters": [],
            "streams": [],
            "group_by": [],
            "series": [],
            "conditions": {"expression": None},
            "search_within_ms": search_within_ms,
            "execute_every_ms": execute_every_ms,
            "event_limit": 1000,
        },
        "field_spec": {
            "ALERT_ID": _template("${source._id}"),
            "CUSTOMER_CODE": _template("${source.syslog_customer}"),
            "ALERT_SOURCE": _template("SOCFORTRESS_WAF"),
            "COPILOT_ALERT_ID": _template("NONE"),
        },
        "key_spec": [],
        "notification_settings": {"grace_period_ms": 0, "backlog_size": None},
        "notifications": [],
    }


def brute_force_definition(notification_id: str) -> dict:
    series_id = "waf-blocks-count"
    return {
        "title": BRUTE_FORCE_TITLE,
        "description": (
            f"{BRUTE_FORCE_THRESHOLD}+ requests from one IP blocked by a customer's SOCFortress WAF "
            f"within {BRUTE_FORCE_WINDOW_MS // 60000} minutes."
        ),
        "priority": 3,
        "alert": True,
        "config": {
            "type": "aggregation-v1",
            "query": f"syslog_type:{SYSLOG_TYPE} AND waf_action:blocked",
            "query_parameters": [],
            "streams": [],
            # syslog_customer is grouped so the customer code is in the event's group-by
            # fields — the only "source" an aggregation event has for its templates.
            "group_by": ["syslog_customer", "waf_client_ip"],
            "series": [{"id": series_id, "type": "count", "field": None}],
            "conditions": {
                "expression": {
                    "expr": ">=",
                    "left": {"expr": "number-ref", "ref": series_id},
                    "right": {"expr": "number", "value": BRUTE_FORCE_THRESHOLD},
                },
            },
            "search_within_ms": BRUTE_FORCE_WINDOW_MS,
            "execute_every_ms": BRUTE_FORCE_EVERY_MS,
            "event_limit": 1000,
        },
        # The threshold route requires exactly these four; COPILOT_ALERT_ID must NOT be
        # set, or the per-event collector would also pick the event up.
        "field_spec": {
            "CUSTOMER_CODE": _template("${source.syslog_customer}"),
            "SOURCE": _template(SYSLOG_TYPE),
            "ALERT_DESCRIPTION": _template(
                f"{BRUTE_FORCE_THRESHOLD}+ blocked requests from ${{source.waf_client_ip}} in {BRUTE_FORCE_WINDOW_MS // 60000} minutes",
            ),
            "ASSET_NAME": _template("${source.waf_client_ip}"),
        },
        "key_spec": [],
        "notification_settings": {"grace_period_ms": 0, "backlog_size": None},
        "notifications": [{"notification_id": notification_id, "notification_parameters": None}],
    }


def threshold_webhook_url() -> str:
    host = (os.environ.get("ALERT_FORWARDING_IP") or "").strip()
    if not host or host == "0.0.0.0":
        raise HTTPException(
            status_code=400,
            detail="ALERT_FORWARDING_IP is not set: Graylog needs CoPilot's address to deliver WAF brute-force alerts "
            f"(it POSTs to http://<ALERT_FORWARDING_IP>:5000{THRESHOLD_ROUTE}).",
        )
    return f"http://{host}:5000{THRESHOLD_ROUTE}"


def threshold_header_value() -> str:
    value = (os.environ.get("GRAYLOG_API_HEADER_VALUE") or "").strip()
    if not value:
        raise HTTPException(
            status_code=400,
            detail="GRAYLOG_API_HEADER_VALUE is not set: the threshold route refuses unauthenticated Graylog webhooks.",
        )
    return value


def notification_payload(url: str, header_value: str) -> dict:
    return {
        "title": THRESHOLD_NOTIFICATION_TITLE,
        "description": "Delivers threshold alerts (e.g. WAF brute force) to CoPilot's threshold route",
        "config": {
            "type": "http-notification-v1",
            "url": url,
            # Sent as the `graylog: <value>` header that verify_graylog_header checks.
            "api_key_as_header": True,
            "api_key": "graylog",
            "api_secret": {"set_value": header_value},
            "skip_tls_verification": False,
        },
    }


async def _ensure_url_allowlisted(url: str) -> None:
    """Graylog refuses a notification whose URL isn't on its allowlist (7.x path, 6.x fallback)."""
    try:
        endpoint = "/api/system/urlallowlist"
        current = (await send_get_request(endpoint))["data"]
    except HTTPException:
        endpoint = "/api/system/urlwhitelist"
        current = (await send_get_request(endpoint))["data"]
    entries = list(current.get("entries", []))
    if current.get("disabled") or any(e.get("type") == "literal" and e.get("value") == url for e in entries):
        return
    entries.append(
        {"id": secrets.token_hex(12), "title": f'"{THRESHOLD_NOTIFICATION_TITLE}" alert notification', "type": "literal", "value": url},
    )
    await send_put_request(endpoint, data={"entries": entries, "disabled": bool(current.get("disabled"))})
    logger.info(f"Added {url} to Graylog's URL allowlist")


async def _find_notification_id(title: str) -> Optional[str]:
    data = (await send_get_request("/api/events/notifications", params={"per_page": 500}))["data"]
    return next((n["id"] for n in data.get("notifications", []) if n.get("title") == title), None)


async def ensure_threshold_notification() -> str:
    url = threshold_webhook_url()
    header_value = threshold_header_value()
    existing = await _find_notification_id(THRESHOLD_NOTIFICATION_TITLE)
    if existing:
        return existing
    await _ensure_url_allowlisted(url)
    created = await send_post_request_create_entity("/api/events/notifications", entity=notification_payload(url, header_value))
    return created["data"]["id"]


async def provision_blocked_alert(execute_every_seconds: int, search_within_seconds: int) -> None:
    await ensure_waf_alert_source()
    await send_post_request_create_entity(
        "/api/events/definitions",
        entity=blocked_definition(execute_every_seconds * 1000, search_within_seconds * 1000),
    )
    logger.info(f"Provisioned Graylog event definition {BLOCKED_TITLE}")


async def provision_brute_force_alert() -> None:
    # Resolve the notification first: a missing ALERT_FORWARDING_IP / header fails
    # before anything is registered or created.
    notification_id = await ensure_threshold_notification()
    await ensure_waf_alert_source()
    await send_post_request_create_entity("/api/events/definitions", entity=brute_force_definition(notification_id))
    logger.info(f"Provisioned Graylog event definition {BRUTE_FORCE_TITLE} (notification {notification_id})")
