"""One customer's weekly report (contract v1), built from its stage-2 leaves, redacted and checked with sysmon-sync's own
validator before anything is sent. Pure: no I/O.

The report has exactly the contract's 7 top-level keys. Totals the contract has no key for (events overall, raw pattern
counts, drops) stay in this CoPilot: in the preview, stats-state.json and the audit row.
"""
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats.contract_v1 import REPORT_FORMAT
from app.active_response.services.sysmon_stats.contract_v1 import ReportRefused
from app.active_response.services.sysmon_stats.contract_v1 import canonical
from app.active_response.services.sysmon_stats.contract_v1 import iso_week
from app.active_response.services.sysmon_stats.contract_v1 import validate_report
from app.active_response.services.sysmon_stats.contract_v1 import week_accepted
from app.active_response.services.sysmon_stats.dns_policy import Drop
from app.active_response.services.sysmon_stats.queries import RawPattern
from app.active_response.services.sysmon_stats.redaction import RedactedPattern
from app.active_response.services.sysmon_stats.redaction import RedactionContext
from app.active_response.services.sysmon_stats.redaction import learn_from_patterns
from app.active_response.services.sysmon_stats.redaction import merge_collisions
from app.active_response.services.sysmon_stats.redaction import redact_pattern

MAX_REPORT_AGE_WEEKS = 2


@dataclass
class LocalStats:
    raw_patterns: int = 0
    sent: int = 0
    merged: int = 0
    truncated: bool = False
    dropped_by_reason: Dict[str, int] = field(default_factory=dict)
    # Event IDs whose patterns could not be collected (a key field not aggregatable): the report is truncated
    unavailable_events: List[int] = field(default_factory=list)


@dataclass
class BuiltReport:
    doc: Dict[str, Any]
    payload: bytes
    sha256: str
    stats: LocalStats


class LocalRefusal(Exception):
    """CoPilot's own report failed sysmon-sync's validator: a bug. Never sent. Carries reason codes and indexes only."""

    def __init__(self, reason: str, problems: Optional[List[Dict[str, Any]]] = None):
        super().__init__(reason)
        self.reason = reason
        self.problems = problems or []


def serialize(doc: Dict[str, Any]) -> bytes:
    """The bytes sent: compact UTF-8 JSON (the contract asks for ensure_ascii=False)."""
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _pattern_json(p: RedactedPattern, report_endpoints: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {"event_id": p.eid, "fields": dict(p.fields)}
    if p.rule_name is not None:
        out["rule_name"] = p.rule_name
    out["events"] = max(1, min(settings.MAX_PATTERN_EVENTS, p.events))
    out["endpoints"] = max(1, min(report_endpoints, p.endpoints))
    out["days"] = p.days
    return out


def _sort_key(p: RedactedPattern):
    return (-p.events, p.eid, canonical(p.key_fields))


def build_report(
    *,
    customer: str,
    week: str,
    config: Union[int, str],
    endpoints: int,
    raw_patterns: List[RawPattern],
    ctx: RedactionContext,
    min_endpoints: int,
    pairs_left_out: bool = False,
    cut_tails: Optional[List[int]] = None,
    unavailable_events: Optional[List[int]] = None,
    today: Optional[date] = None,
) -> BuiltReport:
    """The report, its exact bytes and their sha256. Raises LocalRefusal when it cannot be sent as built."""
    stats = LocalStats(raw_patterns=len(raw_patterns), unavailable_events=sorted(set(unavailable_events or [])))
    drops: Counter = Counter()
    report_endpoints = max(0, min(settings.MAX_REPORT_ENDPOINTS, int(endpoints)))
    monday = iso_week(week)
    if monday is None:
        raise LocalRefusal("week-not-accepted")
    if today is not None and not week_accepted(monday, today, MAX_REPORT_AGE_WEEKS):
        raise LocalRefusal("week-not-accepted")

    # What any value reveals of the customer's own domains redacts every other value, whatever the patterns' order
    learn_from_patterns(ctx, raw_patterns)
    redacted: List[RedactedPattern] = []
    for raw in raw_patterns:
        result = redact_pattern(raw, ctx)
        if isinstance(result, Drop):
            drops[result.reason] += 1
            continue
        if result.days < 1:
            drops["value-invalid"] += 1
            continue
        redacted.append(result)
    merged, stats.merged = merge_collisions(redacted)

    qualifying = []
    for p in merged:
        if p.endpoints < min_endpoints:
            drops["below-min-endpoints"] += 1
            continue
        qualifying.append(p)
    qualifying.sort(key=_sort_key)
    chosen = qualifying[: settings.MAX_PATTERNS]
    # An event left out because a key field cannot be aggregated: its patterns may well be among the noisiest
    truncated = len(qualifying) > settings.MAX_PATTERNS or pairs_left_out or bool(stats.unavailable_events)
    # A stage-1 or stage-2 terms agg that left buckets out: their tail could have held a pattern that would be sent
    smallest = chosen[-1].events if len(chosen) >= settings.MAX_PATTERNS else 0
    if any(tail >= smallest for tail in (cut_tails or [])):
        truncated = True

    doc: Dict[str, Any] = {
        "format": REPORT_FORMAT,
        "customer": customer,
        "week": week,
        "config": config,
        "endpoints": report_endpoints,
        "truncated": truncated,
        "patterns": [_pattern_json(p, report_endpoints) for p in chosen],
    }
    payload = serialize(doc)
    while len(payload) > settings.MAX_REPORT_BYTES and doc["patterns"]:
        doc["patterns"].pop()
        doc["truncated"] = True
        payload = serialize(doc)

    # sysmon-sync's own validator, on exactly what would be sent
    doc, payload = _validated(doc, payload, drops)
    stats.sent = len(doc["patterns"])
    stats.truncated = bool(doc["truncated"])
    stats.dropped_by_reason = dict(sorted(drops.items()))
    return BuiltReport(doc=doc, payload=payload, sha256=hashlib.sha256(payload).hexdigest(), stats=stats)


def _validated(doc: Dict[str, Any], payload: bytes, drops: Counter):
    for attempt in range(2):
        try:
            parsed = validate_report(json.loads(payload))
        except ReportRefused as e:
            raise LocalRefusal(e.reason, e.patterns_json())
        if not parsed.rejected:
            return doc, payload
        if attempt:
            raise LocalRefusal("rejected-after-removal", [p.to_json() for p in parsed.rejected])
        rejected = {p.index for p in parsed.rejected}
        for p in parsed.rejected:
            drops["local-validator-rejected"] += 1
        doc = {**doc, "patterns": [p for i, p in enumerate(doc["patterns"]) if i not in rejected]}
        payload = serialize(doc)
    raise LocalRefusal("rejected-after-removal")  # pragma: no cover - the loop returns or raises
