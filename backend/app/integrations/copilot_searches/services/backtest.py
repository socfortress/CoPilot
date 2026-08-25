"""Backtest a Graylog-only detection rule against a tenant's real data.

Runs the rule's ``graylog.query`` through Graylog's tabular Search API (never
OpenSearch), scoped to the selected customer's Graylog stream, and reports what it
would have done over a time window:

- **total_hits** — exact match count (global count aggregate).
- **sparkline** — matches per time bucket, so spikes are visible.
- **samples / top_fields** — real events + a value breakdown, to tell "one noisy
  host" from "genuine spread".
- **aggregation** (threshold rules) — a local sliding-window simulation using the
  *same* ``count`` / ``distinct_count`` semantics CoPilot provisions to Graylog
  (see copilot_searches._build_aggregation_series_and_conditions): how many alerts
  the threshold would have raised, the top offenders, and threshold sensitivity.

Graylog's tabular aggregate groups by field value only (no server-side time
buckets), so we fetch the matching events once (capped) and window/threshold them
locally. Exact totals come from the count aggregate; per-window/sparkline figures
cover the fetched subset and are labelled ``truncated`` when the cap is hit.
"""
from __future__ import annotations

import re
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import yaml
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.db.universal_models import CustomersMeta
from app.integrations.copilot_searches.services.graylog_search import list_stream_fields
from app.integrations.copilot_searches.services.graylog_search import search_messages

MAX_RANGE_SECONDS = 30 * 86400  # 30 days — hard ceiling (guardrail)
DEFAULT_RANGE_SECONDS = 7 * 86400
FETCH_CAP = 10000  # most events pulled for local analysis
SAMPLE_SIZE = 20
MAX_SAMPLE_FIELDS = 14  # lean field set for the analysis fetch / table columns
MAX_DETAIL_FIELDS = 500  # full field set pulled for the sample-event inspector
# Graylog returns "-" for a requested field that is absent from a document.
_ABSENT = (None, "", "-")
# Graylog stream ids are Mongo ObjectIds (24 hex chars); anything else (e.g. the
# dev placeholder "string") is not a real stream and Graylog will reject it.
_STREAM_ID_RE = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)

_QUERY_FIELD_RE = re.compile(r"([A-Za-z_][\w.]*)\s*:")
_RESERVED = {"AND", "OR", "NOT", "TO", "_exists_"}

_OPS: Dict[str, Callable[[float, float], bool]] = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


# ---------------------------------------------------------------------------
# tenant + parsing helpers
# ---------------------------------------------------------------------------
async def get_customer_stream(customer_code: str) -> Optional[str]:
    """The Graylog stream id for a customer, or None if the customer/stream is unset."""
    async with get_db_session() as session:
        res = await session.execute(select(CustomersMeta).where(CustomersMeta.customer_code == customer_code))
        meta = res.scalars().first()
    return meta.customer_meta_graylog_stream if meta else None


def _parse_window_seconds(value: Any) -> Optional[int]:
    """'10m'/'1h'/'30s'/'1d'/bare-seconds -> seconds. None if unparseable."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    text = str(value or "").strip().lower()
    if not text:
        return None
    try:
        seconds = float(text[:-1]) * _UNITS[text[-1]] if text[-1] in _UNITS else float(text)
    except (ValueError, KeyError):
        return None
    return int(seconds) if seconds > 0 else None


def _schema_names(resp: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for col in resp.get("schema", []) or []:
        if isinstance(col, dict):
            out.append(str(col.get("field") or col.get("name") or col.get("column") or ""))
        else:
            out.append(str(col))
    return out


def _row_to_dict(row: Any, names: List[str]) -> Dict[str, Any]:
    if isinstance(row, dict):
        return row
    if isinstance(row, list):
        return {(names[i] if i < len(names) else f"col{i}"): v for i, v in enumerate(row)}
    return {"value": row}


def _to_epoch(ts: Any) -> Optional[float]:
    """Parse a Graylog timestamp (ISO string / epoch) to epoch seconds."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        return float(ts)
    s = str(ts).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00").replace(" ", "T", 1)
    # normalise a "+0000" style offset (no colon) that fromisoformat rejects.
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def _query_fields(query: str) -> List[str]:
    fields: List[str] = []
    for m in _QUERY_FIELD_RE.findall(query or ""):
        if m not in _RESERVED and m not in fields:
            fields.append(m)
    return fields


def _bucket_unit(range_seconds: int) -> Tuple[str, int]:
    if range_seconds <= 2 * 86400:
        return "1h", 3600
    return "1d", 86400


def _sparkline(rows: List[Tuple[float, Dict[str, Any]]], bucket_seconds: int) -> List[Dict[str, Any]]:
    counts: Dict[int, int] = {}
    for ts, _ in rows:
        key = int(ts // bucket_seconds)
        counts[key] = counts.get(key, 0) + 1
    out = []
    for key in sorted(counts):
        # ISO-8601 UTC so the frontend chart (dayjs) parses it unambiguously.
        label = datetime.fromtimestamp(key * bucket_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append({"bucket": label, "count": counts[key]})
    return out


def _top_fields(samples: List[Dict[str, Any]], candidates: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for field in candidates:
        counts: Dict[str, int] = {}
        for s in samples:
            val = s.get(field)
            if val not in (None, ""):
                counts[str(val)] = counts.get(str(val), 0) + 1
        if len(counts) > 1:
            top = sorted(counts.items(), key=lambda kv: -kv[1])[:5]
            out[field] = [{"value": v, "count": c} for v, c in top]
    return out


# ---------------------------------------------------------------------------
# aggregation (threshold) simulation
# ---------------------------------------------------------------------------
def _sliding_alerts(events: List[Tuple[float, Any]], window: int, threshold: int, op, distinct: bool) -> Tuple[int, int]:
    """Slide a ``window``-wide span over one group's events → (alerts, peak metric).

    Phase-independent (unlike epoch-aligned tumbling): Graylog evaluates a moving
    window, so a burst that would straddle a fixed boundary still fires. Alerts are
    counted greedily on non-overlapping firing windows — one burst = one alert, a
    sustained flood = one alert per window-length it spans.

    metric = event count (``distinct=False``) or number of distinct values
    (``distinct=True``, the ``card()`` case). Two-pointer, O(n) amortised per group.
    """
    events.sort(key=lambda e: e[0])
    n = len(events)
    i = r = alerts = peak = 0
    counts: Dict[Any, int] = {}
    active = 0  # distinct values currently in [i, r)

    def add(idx: int):
        nonlocal active
        v = events[idx][1]
        if counts.get(v, 0) == 0:
            active += 1
        counts[v] = counts.get(v, 0) + 1

    def drop(idx: int):
        nonlocal active
        v = events[idx][1]
        counts[v] -= 1
        if counts[v] == 0:
            active -= 1

    while i < n:
        if r < i:
            r = i
            counts.clear()
            active = 0
        while r < n and events[r][0] < events[i][0] + window:
            if distinct:
                add(r)
            r += 1
        metric = active if distinct else (r - i)
        peak = max(peak, metric)
        if op(metric, threshold):
            alerts += 1
            wend = events[i][0] + window
            while i < n and events[i][0] < wend:  # skip past the fired window
                if distinct:
                    drop(i)
                i += 1
        else:
            if distinct:
                drop(i)
            i += 1
    return alerts, peak


def _simulate_aggregation(
    rows: List[Tuple[float, Dict[str, Any]]],
    agg: Dict[str, Any],
    truncated: bool,
) -> Optional[Dict[str, Any]]:
    """Replay a count/distinct_count threshold over a sliding window, locally."""
    window_seconds = _parse_window_seconds(agg.get("window"))
    if not window_seconds:
        return None
    condition = agg.get("condition") or ">"
    op = _OPS.get(condition, _OPS[">"])
    threshold = agg.get("threshold") or 1
    try:
        threshold = int(threshold)
    except (ValueError, TypeError):
        threshold = 1
    function = (agg.get("function") or "count").lower()
    field = agg.get("field")
    distinct = function == "distinct_count"
    group_by = [g for g in (agg.get("group_by") or []) if g]

    # events per group: (ts, field-value) — value only matters for distinct_count.
    per_group_events: Dict[Tuple, List[Tuple[float, Any]]] = {}
    for ts, row in rows:
        gkey = tuple(str(row.get(g, "")) for g in group_by) if group_by else ("*",)
        val = str(row.get(field, "")) if distinct else None
        per_group_events.setdefault(gkey, []).append((ts, val))

    def alerts_at(th: int) -> int:
        return sum(_sliding_alerts(list(evs), window_seconds, th, op, distinct)[0] for evs in per_group_events.values())

    # per-group alerts + peak at the configured threshold (peak is threshold-independent).
    offenders = []
    estimated = 0
    for gkey, evs in per_group_events.items():
        alerts, peak = _sliding_alerts(list(evs), window_seconds, threshold, op, distinct)
        estimated += alerts
        if alerts > 0:
            label = ", ".join(f"{group_by[i]}={gv}" for i, gv in enumerate(gkey)) if group_by else "(all events)"
            offenders.append({"group": label, "windows_alerting": alerts, "peak": peak})
    offenders.sort(key=lambda o: (-o["windows_alerting"], -o["peak"]))

    # threshold sensitivity — recompute alerts at a few thresholds (no extra queries).
    candidate_ths = sorted({max(1, int(round(threshold * m))) for m in (0.5, 0.75, 1.0, 1.5, 2.0)})
    sensitivity = [{"threshold": th, "alerts": alerts_at(th)} for th in candidate_ths]

    return {
        "window": str(agg.get("window")),
        "window_seconds": window_seconds,
        "function": function,
        "field": field,
        "group_by": group_by,
        "threshold": threshold,
        "condition": condition,
        "estimated_alerts": estimated,
        "top_offenders": offenders[:10],
        "sensitivity": sensitivity,
        "truncated": truncated,
    }


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
async def run_backtest(rule_yaml: str, customer_code: str, range_seconds: int = DEFAULT_RANGE_SECONDS) -> Dict[str, Any]:
    """Backtest a rule YAML for one customer over a relative time window."""
    range_seconds = max(300, min(int(range_seconds or DEFAULT_RANGE_SECONDS), MAX_RANGE_SECONDS))

    def err(msg: str) -> Dict[str, Any]:
        return {"success": False, "message": msg, "error": msg}

    # --- parse the rule ----------------------------------------------------
    try:
        data = yaml.safe_load(rule_yaml)
    except yaml.YAMLError as exc:
        return err(f"Rule YAML is not parseable: {exc}")
    if not isinstance(data, dict):
        return err("Rule must be a YAML mapping.")
    query = ((data.get("graylog") or {}).get("query") or "").strip()
    if not query:
        return err("Rule has no graylog.query to backtest.")
    agg_raw = data.get("aggregation")
    agg_enabled = isinstance(agg_raw, dict) and bool(agg_raw.get("enabled"))

    # --- resolve tenant stream --------------------------------------------
    if not customer_code:
        return err("Select a customer to backtest against.")
    stream = await get_customer_stream(customer_code)
    if not stream:
        return err(f"Customer '{customer_code}' has no Graylog stream configured.")
    if not _STREAM_ID_RE.match(str(stream)):
        return err(
            f"Customer '{customer_code}' has a placeholder/invalid Graylog stream ('{stream}'). "
            "Set a real Graylog stream on the customer to backtest.",
        )

    # --- fetch matching events for analysis -------------------------------
    # Everything (total, sparkline, samples, threshold sim) is derived from the
    # fetched events. The messages endpoint is index-independent; the aggregate
    # endpoint is not (needs keyword fields, rejects empty group_by).
    qfields = _query_fields(query)
    agg_fields = ([f for f in (agg_raw.get("group_by") or []) if f] + ([agg_raw.get("field")] if agg_raw and agg_raw.get("field") else [])) if isinstance(agg_raw, dict) else []
    fetch_fields: List[str] = []
    for f in ["timestamp", "source", "message", *qfields, *agg_fields]:
        if f and f not in fetch_fields:
            fetch_fields.append(f)
    fetch_fields = fetch_fields[:MAX_SAMPLE_FIELDS]

    rows: List[Tuple[float, Dict[str, Any]]] = []
    sample_fields: List[str] = fetch_fields
    fetched = 0
    try:
        msg_resp = await search_messages(query=query, streams=[stream], fields=fetch_fields, size=FETCH_CAP, range_seconds=range_seconds)
        sample_fields = _schema_names(msg_resp) or fetch_fields
        datarows = msg_resp.get("datarows") or []
        fetched = len(datarows)
        for r in datarows:
            d = _row_to_dict(r, sample_fields)
            ts = _to_epoch(d.get("timestamp"))
            if ts is not None:
                rows.append((ts, d))
    except Exception as exc:  # noqa: BLE001 — surface a clean error to the UI
        logger.warning(f"[backtest] messages fetch failed: {exc}")
        return err(f"Graylog search failed: {getattr(exc, 'detail', exc)}")

    # total = fetched events; when we hit the fetch cap it's a lower bound.
    truncated = fetched >= FETCH_CAP
    total = fetched

    # --- derive views ------------------------------------------------------
    bucket_unit, bucket_seconds = _bucket_unit(range_seconds)
    per_bucket = _sparkline(rows, bucket_seconds)
    samples = [d for _, d in rows[:SAMPLE_SIZE]]
    top_fields = _top_fields([d for _, d in rows], ["source", *qfields[:3]])

    # --- rich samples: pull the FULL field set for the sample events so the UI
    #     can show a full-log inspector (bounded second fetch; best-effort). -----
    try:
        stream_fields = await list_stream_fields(stream)
        if stream_fields:
            detail_fields: List[str] = []
            for f in ["timestamp", "source", "message", "full_message", *stream_fields]:
                if f and f not in detail_fields:
                    detail_fields.append(f)
            detail_fields = detail_fields[:MAX_DETAIL_FIELDS]
            rich_resp = await search_messages(query=query, streams=[stream], fields=detail_fields, size=SAMPLE_SIZE, range_seconds=range_seconds)
            rnames = _schema_names(rich_resp) or detail_fields
            rich: List[Dict[str, Any]] = []
            for r in (rich_resp.get("datarows") or [])[:SAMPLE_SIZE]:
                d = _row_to_dict(r, rnames)
                rich.append({k: v for k, v in d.items() if v not in _ABSENT})
            if rich:
                samples = rich
    except Exception as exc:  # noqa: BLE001 — enrichment only; keep the lean samples
        logger.warning(f"[backtest] rich sample fetch failed (non-fatal): {exc}")

    aggregation = None
    if agg_enabled:
        aggregation = _simulate_aggregation(rows, agg_raw, truncated)
        if aggregation is not None:
            days = max(1.0, range_seconds / 86400)
            aggregation["per_day_alerts"] = round(aggregation["estimated_alerts"] / days, 2)

    days = max(1.0, range_seconds / 86400)
    note = None
    if truncated:
        note = (f"Hit the {FETCH_CAP:,}-event analysis cap — this rule matches at least this many events in the window. "
                "Figures are a lower bound over the most recent events; tighten the query or shorten the window for exact numbers.")
    elif agg_enabled and aggregation is None:
        note = "Aggregation block present but its window is unparseable — showing raw event volume only."

    return {
        "success": True,
        "message": "Backtest complete",
        "mode": "aggregation" if aggregation else "messages",
        "customer_code": customer_code,
        "stream_id": stream,
        "range_seconds": range_seconds,
        "query": query,
        "total_hits": total,
        "per_day_avg": round(total / days, 2),
        "fetched": fetched,
        "truncated": truncated,
        "per_bucket": per_bucket,
        "bucket_unit": bucket_unit,
        "samples": samples,
        "sample_fields": sample_fields,
        "top_fields": top_fields,
        "aggregation": aggregation,
        "note": note,
        "error": None,
    }
