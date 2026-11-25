"""Grouped (aggregation) CoPilot Searches events into CoPilot alerts.

A CoPilot Search with ``aggregation.group_by`` provisions a Graylog aggregation event definition. Graylog writes its
events to ``gl-events`` with no ``origin_context`` (there is no single message behind a group), so CoPilot's own
collector (``/incidents/alerts/create/auto``), which builds every alert from the log ``origin_context`` names, can't
read them. This module collects them the same way that collector works, from inside CoPilot Searches:

* **Queue.** ``gl-events`` documents whose ``fields.COPILOT_ALERT_ID`` is ``GROUPED`` (what provisioning writes for a
  grouped rule, so CoPilot's collector, which reads ``NONE`` only, never sees them), or ``NONE`` with no
  ``origin_context`` and a ``fields.RULE_ID`` (grouped CoPilot Searches events provisioned before this module), oldest
  first. Nothing else is read: single-event rules stay with CoPilot's collector.
* **Claim.** Each event is claimed with a conditional update (``PROCESSING:<epoch>``, on the document's sequence
  number), so two backends never build the same alert; a claim older than ``CLAIM_STALE_SECONDS`` (a process that
  died mid-way) is taken again.
* **Alert.** One contributing log is looked up from the event's ``replay_info`` (query, time range, streams) and
  ``group_by_fields``. The customer comes from the group-by fields, else that log, else the event's
  ``CUSTOMER_CODE``, through ingest's own rules (``resolve_customer_code``); the asset from a group-by field that is
  a configured asset field, else that log's asset fields, else ``No asset found``. The title is the search's title
  without the group values and count (``M365 - MASS - FILE - DOWNLOAD``), so repeated firings add to one open alert,
  as single-event alerts do; the group values and the count are kept in the alert context.
* **Stamp.** The CoPilot alert id is written to ``fields.COPILOT_ALERT_ID``, as CoPilot's collector does. An event
  that can never become an alert (no customer) is stamped ``FAILED``, and so is one that failed
  ``MAX_ATTEMPTS`` times; one that failed on what looks like an outage goes back to the queue unchanged.

The collector runs in the backend process every ``INTERVAL_SECONDS``, started by ``start_grouped_alert_collector``
(from ``RulesCache.ensure_loaded``, which CoPilot runs at startup and on its catalog refresh job). It needs no
configuration: ``COPILOT_SEARCHES_GROUPED_ALERTS=false`` turns it off.
"""

import asyncio
import os
import re
import time
from collections import OrderedDict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from loguru import logger
from pydantic import ValidationError

GROUPED_MARKER = "GROUPED"
NONE_MARKER = "NONE"
PROCESSING_PREFIX = "PROCESSING:"
FAILED_MARKER = "FAILED"
NO_ASSET = "No asset found"
CONTEXT_KEY = "copilot_search_grouped_event"

INTERVAL_SECONDS = 60
FIRST_RUN_DELAY_SECONDS = 30
BATCH_SIZE = 100
MAX_EVENTS_PER_RUN = 500
CLAIM_STALE_SECONDS = 900
MAX_ATTEMPTS = 5
SEARCH_TIMEOUT_SECONDS = 30
STREAM_CACHE_SECONDS = 600

# A contributing log is searched in the indices of the event's streams; when those can't be read from Graylog, in
# every alert index (CoPilot Searches' firing-stats pattern) minus Graylog's own.
FALLBACK_INDEX_PATTERN = (
    "*,-.*,-_*,-wazuh-monitoring-*,-wazuh-statistics-*,-wazuh-states-*,-wazuh-vulnerabilities-*,-security-auditlog-*,-gl-*"
)
RANGE_FORMAT = "strict_date_optional_time||yyyy-MM-dd HH:mm:ss.SSS||yyyy-MM-dd HH:mm:ss"

# " - count()=26.0" (and ", card(field)=3" for several series) at the end of an aggregation event's message.
_SERIES = re.compile(r"\s+-\s+[A-Za-z_]+\([^()]*\)\s*=\s*[^,\s]+(?:\s*,\s*[A-Za-z_]+\([^()]*\)\s*=\s*[^,\s]+)*\s*$")

_TASK: Optional["asyncio.Task[None]"] = None
_ATTEMPTS: "OrderedDict[Tuple[str, str], int]" = OrderedDict()
_MAX_TRACKED = 10_000
_STREAM_INDEX: Dict[str, Tuple[float, Optional[str]]] = {}


class GroupedEventUnresolvable(Exception):
    """The event names nothing CoPilot can file an alert under (no customer): retrying can't help."""

    permanent = True


# --- what an event says (pure) ----------------------------------------------------------------------------------------


def grouped_alert_title(message: str, group_by_fields: Dict[str, Any]) -> str:
    """The search's title from an aggregation event's message ``<title>: <group values> - count()=N``: the series and
    the group values cut off, so every firing of the search carries the same title. A message in another shape is
    kept as it is (only a trailing series is cut)."""
    message = (message or "").strip()
    match = _SERIES.search(message)
    rest = message[: match.start()] if match else message
    values = [str(v) for v in group_by_fields.values() if v not in (None, "")]
    if values:
        idx = rest.rfind(": ")
        while idx > 0:
            if all(v in rest[idx + 2 :] for v in values):
                return rest[:idx].strip() or message
            idx = rest.rfind(": ", 0, idx)
    return rest.strip() or message


def series_text(message: str) -> Optional[str]:
    """``count()=26.0`` from the end of an aggregation event's message, if there."""
    match = _SERIES.search((message or "").strip())
    return match.group(0).strip().lstrip("-").strip() if match else None


def group_values(source: Dict[str, Any]) -> Dict[str, Any]:
    raw = source.get("group_by_fields")
    return {str(k): v for k, v in raw.items() if v not in (None, "")} if isinstance(raw, dict) else {}


def event_context(index: str, doc_id: str, source: Dict[str, Any]) -> Dict[str, Any]:
    """What the alert keeps of the grouped event: its group values, the count, the search and its window."""
    fields = source.get("fields") if isinstance(source.get("fields"), dict) else {}
    replay = source.get("replay_info") if isinstance(source.get("replay_info"), dict) else {}
    return {
        "group_by_fields": group_values(source),
        "series": series_text(source.get("message") or ""),
        "message": source.get("message"),
        "rule_id": fields.get("RULE_ID"),
        "alert_source": fields.get("ALERT_SOURCE"),
        "event_definition_id": source.get("event_definition_id"),
        "replay_query": replay.get("query"),
        "timerange_start": replay.get("timerange_start") or source.get("timerange_start"),
        "timerange_end": replay.get("timerange_end") or source.get("timerange_end"),
        "gl_event": f"{index}/{doc_id}",
    }


def asset_from_group(group: Dict[str, Any], asset_fields: List[str]) -> Optional[str]:
    """The value of the first configured asset field the event is grouped by."""
    for field in asset_fields:
        value = group.get(field)
        if value not in (None, ""):
            return str(value)
    return None


def split_fields(value: Optional[str]) -> List[str]:
    return [f.strip() for f in (value or "").split(",") if f.strip()]


def queue_query(now: Optional[float] = None) -> Dict[str, Any]:
    """The grouped CoPilot Searches events still to collect, oldest first: ``GROUPED``; ``NONE`` without an
    ``origin_context`` but with a ``RULE_ID``; or a claim older than ``CLAIM_STALE_SECONDS`` (fixed-width epochs
    compare as text)."""
    stale_before = int((now if now is not None else time.time()) - CLAIM_STALE_SECONDS)
    return {
        "query": {
            "bool": {
                "should": [
                    {"term": {"fields.COPILOT_ALERT_ID": GROUPED_MARKER}},
                    {
                        "bool": {
                            "filter": [{"term": {"fields.COPILOT_ALERT_ID": NONE_MARKER}}, {"exists": {"field": "fields.RULE_ID"}}],
                            "must_not": [{"exists": {"field": "origin_context"}}],
                        },
                    },
                    {
                        "range": {
                            "fields.COPILOT_ALERT_ID": {
                                "gte": f"{PROCESSING_PREFIX}0000000000",
                                "lt": f"{PROCESSING_PREFIX}{stale_before:010d}",
                            },
                        },
                    },
                ],
                "minimum_should_match": 1,
            },
        },
        "sort": [{"timestamp": {"order": "asc"}}],
    }


def log_query(source: Dict[str, Any], group: Dict[str, Any], streams: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    """One log that counted towards the grouped event: the replayed search, in its window, with the group's values
    (and, when given, from its streams). ``None`` when the event has no window to search."""
    replay = source.get("replay_info") if isinstance(source.get("replay_info"), dict) else {}
    start = replay.get("timerange_start") or source.get("timerange_start")
    end = replay.get("timerange_end") or source.get("timerange_end")
    if not start or not end:
        return None
    filters: List[Dict[str, Any]] = [
        {"query_string": {"query": replay.get("query") or "*", "default_operator": "AND", "analyze_wildcard": True}},
        {"range": {"timestamp": {"gte": str(start), "lte": str(end), "format": RANGE_FORMAT}}},
    ]
    filters += [{"match_phrase": {field: value}} for field, value in group.items()]
    if streams:
        filters.append({"terms": {"streams": list(streams)}})
    return {"query": {"bool": {"filter": filters}}, "sort": [{"timestamp": {"order": "asc"}}], "_source": False}


# --- failures ---------------------------------------------------------------------------------------------------------


def looks_transient(exc: BaseException) -> bool:
    """A failure that looks like an outage (the indexer, Graylog or the database unreachable or timing out, anywhere
    in the exception's chain): the event goes back to the queue without counting an attempt."""
    names = {
        "ConnectionError",
        "ConnectionTimeout",
        "ConnectTimeout",
        "ReadTimeout",
        "SSLError",
        "OperationalError",
        "InterfaceError",
        "DisconnectionError",
        "TimeoutError",
        "PoolTimeout",
    }
    current: Optional[BaseException] = exc
    for _ in range(8):
        if current is None:
            break
        if isinstance(current, (asyncio.TimeoutError, TimeoutError, ConnectionError)) or type(current).__name__ in names:
            return True
        current = current.__cause__ or current.__context__
    return False


def is_permanent(exc: BaseException) -> bool:
    return isinstance(exc, ValidationError) or getattr(exc, "permanent", False) is True


def count_attempt(index: str, doc_id: str) -> int:
    key = (index, doc_id)
    count = _ATTEMPTS.pop(key, 0) + 1
    _ATTEMPTS[key] = count
    while len(_ATTEMPTS) > _MAX_TRACKED:
        _ATTEMPTS.popitem(last=False)
    return count


def failure_outcome(index: str, doc_id: str, exc: BaseException) -> str:
    """``FAILED`` (never retried) or the event's queue marker back (retried): permanent failures and the
    ``MAX_ATTEMPTS``-th failure are final, outages never count."""
    if is_permanent(exc):
        _ATTEMPTS.pop((index, doc_id), None)
        return FAILED_MARKER
    if looks_transient(exc):
        return "retry"
    if count_attempt(index, doc_id) >= MAX_ATTEMPTS:
        _ATTEMPTS.pop((index, doc_id), None)
        return FAILED_MARKER
    return "retry"


# --- the indexer and Graylog ------------------------------------------------------------------------------------------


async def _stream_index_pattern(stream_id: str) -> Optional[str]:
    """``<index prefix>_*`` of a Graylog stream's index set, cached ``STREAM_CACHE_SECONDS`` (``None``: unknown)."""
    cached = _STREAM_INDEX.get(stream_id)
    if cached is not None and time.monotonic() - cached[0] < STREAM_CACHE_SECONDS:
        return cached[1]
    from app.connectors.graylog.utils.universal import send_get_request

    pattern: Optional[str] = None
    try:
        stream = (await send_get_request(endpoint=f"/api/streams/{stream_id}"))["data"]
        index_set_id = stream.get("index_set_id") if isinstance(stream, dict) else None
        if index_set_id:
            index_set = (await send_get_request(endpoint=f"/api/system/indices/index_sets/{index_set_id}"))["data"]
            prefix = index_set.get("index_prefix") if isinstance(index_set, dict) else None
            if prefix:
                pattern = f"{prefix}_*"
    except Exception as exc:  # noqa: BLE001 - an unreadable stream only widens the search
        logger.warning(f"CoPilot Searches grouped alerts: could not read Graylog stream {stream_id} ({type(exc).__name__})")
    _STREAM_INDEX[stream_id] = (time.monotonic(), pattern)
    return pattern


async def find_contributing_log(es: Any, source: Dict[str, Any], group: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """``(index, _id)`` of one log behind the grouped event, or ``None``: searched in its streams' indices (only its
    streams' messages, then any message there), else every alert index."""
    replay = source.get("replay_info") if isinstance(source.get("replay_info"), dict) else {}
    streams = [s for s in (replay.get("streams") or source.get("source_streams") or []) if isinstance(s, str)]
    patterns = [p for p in [await _stream_index_pattern(s) for s in streams] if p]
    attempts: List[Tuple[str, Optional[List[str]]]] = []
    if patterns:
        attempts += [(",".join(sorted(set(patterns))), streams), (",".join(sorted(set(patterns))), None)]
    attempts.append((FALLBACK_INDEX_PATTERN, streams or None))
    for index, stream_filter in attempts:
        body = log_query(source, group, stream_filter)
        if body is None:
            return None
        try:
            response = await es.search(
                index=index,
                body=body,
                size=1,
                ignore_unavailable=True,
                allow_no_indices=True,
                request_timeout=SEARCH_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 - try the next, wider search
            logger.warning(f"CoPilot Searches grouped alerts: log search in '{index[:80]}' failed ({type(exc).__name__})")
            continue
        hits = response.get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_index"], hits[0]["_id"]
    return None


async def _all_asset_fields(session: Any) -> List[str]:
    from sqlmodel import select

    from app.incidents.models import AssetFieldName

    rows = (await session.execute(select(AssetFieldName.field_name).distinct())).scalars().all()
    seen: List[str] = []
    for row in rows:
        for field in split_fields(row):
            if field not in seen:
                seen.append(field)
    return seen


# --- building the alert -----------------------------------------------------------------------------------------------


async def _payload_from_log(
    details: Any,
    log_source: Dict[str, Any],
    group: Dict[str, Any],
    title: str,
    context: Dict[str, Any],
    timestamp: str,
    session: Any,
):
    """The alert from the contributing log, as CoPilot builds a single-event alert, with the search's title, the
    grouped event's context and an asset that never fails the alert."""
    from app.incidents.schema.incident_alert import CreatedAlertPayload
    from app.incidents.services.incident_alert import build_alert_context_payload
    from app.incidents.services.incident_alert import build_ioc_payload
    from app.incidents.services.incident_alert import get_all_field_names
    from app.incidents.services.incident_alert import resolve_asset_name_from_payload
    from app.incidents.services.notification_enrichment import extract_rule_level
    from app.incidents.services.notification_enrichment import severity_from_rule_level

    field_names = await get_all_field_names(details.syslog_type, session)
    asset_fields = split_fields(field_names.asset_name)
    asset = asset_from_group(group, asset_fields)
    if not asset:
        asset = await resolve_asset_name_from_payload(field_names.asset_name or "", log_source) or NO_ASSET
    alert_context = await build_alert_context_payload(log_source, field_names)
    alert_context[CONTEXT_KEY] = context
    rule_level = extract_rule_level(log_source)
    return CreatedAlertPayload(
        alert_context_payload=alert_context,
        asset_payload=str(asset),
        timefield_payload=timestamp,
        alert_title_payload=title,
        ioc_payload=await build_ioc_payload(log_source, field_names),
        source=str(details.syslog_type)[:50],
        index_name=details.index,
        index_id=details.id,
        rule_level=rule_level,
        severity=severity_from_rule_level(rule_level),
    )


async def _payload_from_event(
    index: str,
    doc_id: str,
    source: Dict[str, Any],
    group: Dict[str, Any],
    title: str,
    context: Dict[str, Any],
    timestamp: str,
    session: Any,
):
    """The alert from the grouped event alone (no contributing log found, or its source isn't configured)."""
    from app.incidents.schema.incident_alert import CreatedAlertPayload

    fields = source.get("fields") if isinstance(source.get("fields"), dict) else {}
    asset = asset_from_group(group, await _all_asset_fields(session)) or NO_ASSET
    alert_context: Dict[str, Any] = {k: str(v) for k, v in group.items()}
    alert_context[CONTEXT_KEY] = context
    return CreatedAlertPayload(
        alert_context_payload=alert_context,
        asset_payload=asset,
        timefield_payload=timestamp,
        alert_title_payload=title,
        ioc_payload=None,
        source=str(fields.get("ALERT_SOURCE") or "copilot_searches").lower()[:50],
        index_name=index,
        index_id=doc_id,
    )


async def create_alert_from_grouped_event(es: Any, hit: Dict[str, Any], session: Any) -> int:
    """The CoPilot alert for one grouped event (a new one, or the open alert with the same title and customer, which
    it is added to). Raises ``GroupedEventUnresolvable`` when no customer can be found."""
    from fastapi import HTTPException

    from app.incidents.schema.incident_alert import CreateAlertRequest
    from app.incidents.services.incident_alert import add_alert_to_document
    from app.incidents.services.incident_alert import add_asset_to_copilot_alert
    from app.incidents.services.incident_alert import add_ioc_to_copilot_alert
    from app.incidents.services.incident_alert import create_alert_full
    from app.incidents.services.incident_alert import get_single_alert_details
    from app.incidents.services.incident_alert import is_customer_code_valid
    from app.incidents.services.incident_alert import open_alert_exists
    from app.incidents.services.incident_alert import resolve_customer_code
    from app.incidents.services.incident_alert import update_alert_creation_time
    from app.incidents.services.incident_alert import validate_syslog_type_source
    from app.incidents.services.threshold_alert import save_threshold_metadata

    index, doc_id = hit["_index"], hit["_id"]
    source = hit.get("_source") or {}
    fields = source.get("fields") if isinstance(source.get("fields"), dict) else {}
    group = group_values(source)
    title = grouped_alert_title(source.get("message") or "", group)
    context = event_context(index, doc_id, source)
    timestamp = str(source.get("timestamp") or "")

    customer = await resolve_customer_code(group, session)
    details = None
    log_source: Dict[str, Any] = {}
    log_ref = await find_contributing_log(es, source, group)
    if log_ref is not None:
        try:
            details = await get_single_alert_details(CreateAlertRequest(index_name=log_ref[0], alert_id=log_ref[1]))
            log_source = details.source.to_dict()
        except HTTPException as exc:
            logger.warning(
                f"CoPilot Searches grouped alerts: contributing log {log_ref[1]} unreadable ({exc.detail}); using the event alone",
            )
            details = None
    if not customer and log_source:
        customer = await resolve_customer_code(log_source, session)
    if not customer and fields.get("CUSTOMER_CODE"):
        customer = str(fields["CUSTOMER_CODE"])
    if not customer:
        raise GroupedEventUnresolvable(
            "no customer: the search is not grouped by a customer field and no contributing log names one "
            "(group by agent_labels_customer, syslog_customer or customer_code to fix the search)",
        )
    await is_customer_code_valid(customer_code=customer, session=session)

    payload = None
    if details is not None:
        try:
            await validate_syslog_type_source(details.syslog_type, session)
            payload = await _payload_from_log(details, log_source, group, title, context, timestamp, session)
        except HTTPException as exc:
            logger.warning(
                f"CoPilot Searches grouped alerts: source '{details.syslog_type}' not usable ({exc.detail}); using the event alone",
            )
            details = None
    if payload is None:
        payload = await _payload_from_event(index, doc_id, source, group, title, context, timestamp, session)

    existing = await open_alert_exists(payload, customer, session)
    if existing:
        await update_alert_creation_time(existing, payload.timefield_payload, session)
        await add_asset_to_copilot_alert(payload, existing, customer, session)
        if payload.ioc_payload is not None:
            await add_ioc_to_copilot_alert(payload, existing, customer, session)
        if details is not None:
            await add_alert_to_document(CreateAlertRequest(index_name=details.index, alert_id=details.id), existing)
        return existing

    # threshold_alert=True: the alert has no single source document to write back to (the event's own is stamped
    # by the caller; the contributing log, when there is one, just below).
    alert_id = await create_alert_full(payload, customer, session, threshold_alert=True)
    if details is not None:
        await add_alert_to_document(CreateAlertRequest(index_name=details.index, alert_id=details.id), alert_id)
        try:
            from datetime import datetime

            def _dt(value: Any) -> datetime:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

            await save_threshold_metadata(
                alert_id=alert_id,
                event_definition_id=str(source.get("event_definition_id") or ""),
                replay_query=str(context.get("replay_query") or "*"),
                timerange_start=_dt(context["timerange_start"]),
                timerange_end=_dt(context["timerange_end"]),
                group_by_fields=group,
                source_streams=list(source.get("source_streams") or []),
                source=str(details.syslog_type)[:50],
                resolved_index_name=details.index,
                resolved_index_id=details.id,
                session=session,
            )
        except Exception as exc:  # noqa: BLE001 - the alert stands without its timeline record
            logger.warning(f"CoPilot Searches grouped alerts: no timeline record for alert {alert_id} ({type(exc).__name__}: {exc})")
    return alert_id


# --- the collector ----------------------------------------------------------------------------------------------------


async def _claim(es: Any, hit: Dict[str, Any]) -> bool:
    """Take the event for this process (``PROCESSING:<epoch>``) unless another took or stamped it first."""
    seq_no, primary_term = hit.get("_seq_no"), hit.get("_primary_term")
    if seq_no is None or primary_term is None:
        return False
    try:
        await es.update(
            index=hit["_index"],
            id=hit["_id"],
            body={"doc": {"fields": {"COPILOT_ALERT_ID": f"{PROCESSING_PREFIX}{int(time.time()):010d}"}}},
            if_seq_no=seq_no,
            if_primary_term=primary_term,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        if type(exc).__name__ == "ConflictError":
            return False
        if "blocked" in str(exc).lower() or "read_only" in str(exc).lower() or "read-only" in str(exc).lower():
            # A rotated gl-events index Graylog made read-only: no claim can be written, so the event is built
            # unclaimed (CoPilot's own collector does the same) and stamped through the write-block workaround.
            return True
        logger.warning(f"CoPilot Searches grouped alerts: could not claim gl-event {hit['_id']} ({type(exc).__name__})")
        return False


async def _stamp(index: str, doc_id: str, value: str) -> None:
    from app.incidents.schema.incident_alert import CreateAlertRequest
    from app.incidents.services.alert_collection import add_copilot_alert_id

    await add_copilot_alert_id(index_data=CreateAlertRequest(index_name=index, alert_id=doc_id), alert_id=value)


async def handle_event(es: Any, hit: Dict[str, Any]) -> str:
    """Build the alert for one claimed event and stamp the event: the alert id, ``FAILED``, or ``GROUPED`` to be
    retried. Returns what was written."""
    from app.db.db_session import get_db_session

    index, doc_id = hit["_index"], hit["_id"]
    try:
        async with get_db_session() as session:
            alert_id = await create_alert_from_grouped_event(es, hit, session)
    except Exception as exc:  # noqa: BLE001 - one event must never stop the run
        outcome = failure_outcome(index, doc_id, exc)
        # Retried as GROUPED, never NONE: an event this module has taken stays out of CoPilot's own queue.
        value = FAILED_MARKER if outcome == FAILED_MARKER else GROUPED_MARKER
        if value == FAILED_MARKER:
            logger.error(
                f"CoPilot Searches grouped alerts: gl-event {doc_id} in '{index}' can't become an alert "
                f"({type(exc).__name__}: {exc}); marked {FAILED_MARKER}",
            )
        else:
            logger.warning(
                f"CoPilot Searches grouped alerts: gl-event {doc_id} in '{index}' failed ({type(exc).__name__}: {exc}); retried next run",
            )
        await _stamp(index, doc_id, value)
        return value
    _ATTEMPTS.pop((index, doc_id), None)
    await _stamp(index, doc_id, str(alert_id))
    logger.info(f"CoPilot Searches grouped alerts: gl-event {doc_id} in '{index}' -> CoPilot alert {alert_id}")
    return str(alert_id)


async def collect_grouped_alerts_once() -> int:
    """One run: up to ``MAX_EVENTS_PER_RUN`` queued grouped events, oldest first. Returns how many were handled."""
    from app.connectors.wazuh_indexer.utils.universal import (
        create_wazuh_indexer_client_async,
    )
    from app.connectors.wazuh_indexer.utils.universal import (
        return_graylog_events_index_names,
    )

    indices = await return_graylog_events_index_names()
    if not indices:
        return 0
    es = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    handled = 0
    seen: Set[Tuple[str, str]] = set()
    try:
        while handled < MAX_EVENTS_PER_RUN:
            response = await es.search(
                index=",".join(indices),
                body=queue_query(),
                size=BATCH_SIZE,
                seq_no_primary_term=True,
                ignore_unavailable=True,
                allow_no_indices=True,
            )
            hits = [h for h in response.get("hits", {}).get("hits", []) if (h["_index"], h["_id"]) not in seen]
            if not hits:
                break
            for hit in hits:
                seen.add((hit["_index"], hit["_id"]))
                if await _claim(es, hit):
                    await handle_event(es, hit)
                    handled += 1
                if handled >= MAX_EVENTS_PER_RUN:
                    break
    finally:
        await es.close()
    if handled:
        logger.info(f"CoPilot Searches grouped alerts: handled {handled} grouped event(s)")
    return handled


def collector_enabled() -> bool:
    return os.getenv("COPILOT_SEARCHES_GROUPED_ALERTS", "true").strip().lower() not in ("false", "0", "no", "off")


async def _run_forever() -> None:
    await asyncio.sleep(FIRST_RUN_DELAY_SECONDS)
    while True:
        try:
            await collect_grouped_alerts_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - the loop must outlive any one run
            logger.warning(f"CoPilot Searches grouped alerts: run failed ({type(exc).__name__}: {exc})")
        await asyncio.sleep(INTERVAL_SECONDS)


def start_grouped_alert_collector() -> bool:
    """Start the collector once per process, from inside the running event loop (idempotent). Returns whether it is
    running. Not started under pytest or when ``COPILOT_SEARCHES_GROUPED_ALERTS`` is false."""
    global _TASK
    if not collector_enabled() or os.getenv("PYTEST_CURRENT_TEST"):
        return False
    if _TASK is not None and not _TASK.done():
        return True
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    _TASK = loop.create_task(_run_forever())
    logger.info(f"CoPilot Searches grouped alerts: collector started (every {INTERVAL_SECONDS}s)")
    return True
