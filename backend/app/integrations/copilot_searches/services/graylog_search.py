"""Graylog tabular Search API calls for the detection-rule backtest.

Self-contained to the copilot_searches feature: it does NOT change any shared
connector logic. It reads the Graylog connector config via the existing read-only
helper and issues its own authenticated POST with ``Accept: application/json``
(the tabular Search API negotiates to CSV otherwise — which the shared
``send_post_request`` can't request). All searching goes through Graylog's Search
API; OpenSearch is never queried directly.

Note: the tabular *aggregate* endpoint groups by field value only (no server-side
time bucketing), so the backtest fetches matching events once and does its own
time-windowing / threshold simulation locally (see services/backtest.py).
"""
from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests
from fastapi import HTTPException
from loguru import logger

from app.blocking import run_blocking
from app.connectors.graylog.utils.routing import get_current_graylog_connector
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

_TIMEOUT = 60
_HEADERS = {"X-Requested-By": "CoPilot", "Accept": "application/json"}


def _relative(range_seconds: int) -> Dict[str, Any]:
    return {"type": "relative", "range": int(range_seconds)}


async def _post(endpoint: str, body: Dict[str, Any], connector_name: Optional[str] = None) -> Dict[str, Any]:
    """POST to a Graylog endpoint with JSON accept; returns the parsed JSON body."""
    if connector_name is None:
        connector_name = get_current_graylog_connector()
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(status_code=500, detail=f"Graylog connector '{connector_name}' not found")

    response = await run_blocking(
        requests.post,
        f"{attributes['connector_url']}{endpoint}",
        headers=_HEADERS,
        auth=(attributes["connector_username"], attributes["connector_password"]),
        json=body,
        verify=False,
        timeout=_TIMEOUT,
    )
    if response.status_code != 200:
        detail = response.text
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = body.get("message", detail)
            elif isinstance(body, list) and body and isinstance(body[0], dict):
                # Graylog validation errors come back as a list of {message, path, ...}.
                first = body[0]
                msg, path = first.get("message", ""), first.get("path", "")
                detail = f"{msg} ({path})" if path else (msg or detail)
        except ValueError:
            pass
        raise HTTPException(status_code=502, detail=f"Graylog search failed ({response.status_code}): {detail}")
    try:
        return response.json() or {}
    except ValueError:
        raise HTTPException(status_code=502, detail="Graylog returned a non-JSON search response.")


async def search_messages(
    query: str,
    streams: List[str],
    fields: List[str],
    size: int = 1000,
    range_seconds: int = 604800,
    connector_name: Optional[str] = None,
) -> Dict[str, Any]:
    """POST /api/search/messages — matching messages for the query, as {schema, datarows}.

    The messages endpoint is used for the whole backtest: it is index-independent
    (unlike /api/search/aggregate, which requires keyword fields and rejects an
    empty group_by), so total/sparkline/threshold-sim are all derived from the
    fetched events locally in services/backtest.py.
    """
    body = {
        "query": query or "",
        "streams": [s for s in streams if s],
        "timerange": _relative(range_seconds),
        "fields": fields,
        "size": int(size),
    }
    logger.info(f"[backtest] messages search over {len(body['streams'])} stream(s), size={size}, range={range_seconds}s")
    return await _post("/api/search/messages", body, connector_name)


async def list_stream_fields(stream: str, connector_name: Optional[str] = None) -> List[str]:
    """Field names present in a stream's data (POST /api/views/fields).

    Used to pull the *complete* set of fields for the sample events so the UI can
    show a full-log inspector. Returns [] on any error (caller falls back).
    """
    if not stream:
        return []
    try:
        data = await _post("/api/views/fields", {"streams": [stream]}, connector_name)
    except Exception as exc:  # noqa: BLE001 — non-fatal enrichment
        logger.warning(f"[backtest] list_stream_fields failed: {exc}")
        return []
    names: List[str] = []
    for f in data or []:
        if isinstance(f, dict) and f.get("name"):
            names.append(str(f["name"]))
    return names
