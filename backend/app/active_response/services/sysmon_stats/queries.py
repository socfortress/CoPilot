"""The indexer aggregations of the weekly Sysmon noise statistics, and their answers' parsers. Pure: no I/O.

Aggregations only (``size: 0``), per customer, bounded sizes, in two stages: stage 1 finds the customer's top (event ID,
actor) pairs, stage 2 the patterns below them. Filters that must work on keyword and numeric mappings alike are
``terms`` lists, never ranges (a keyword range compares text: "10" < "5").
"""
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats.fields import EVENT_IDS
from app.active_response.services.sysmon_stats.fields import EVENT_PLAN
from app.active_response.services.sysmon_stats.fields import SYSMON_CHANNEL
from app.active_response.services.sysmon_stats.fields import FieldMap

MISSING = "-"
USER_DETAILS = ("User", "SourceUser", "TargetUser")


def _week_filter(fm: FieldMap, start_ms: int, end_ms: int) -> Dict[str, Any]:
    return {"range": {fm.time: {"gte": start_ms, "lt": end_ms, "format": "epoch_millis"}}}


def _channel_filter(fm: FieldMap) -> Dict[str, Any]:
    return {"term": {fm.channel: SYSMON_CHANNEL}}


def _base(filters: List[Dict[str, Any]], aggs: Dict[str, Any]) -> Dict[str, Any]:
    return {"size": 0, "track_total_hits": False, "query": {"bool": {"filter": filters}}, "aggs": aggs}


def stage0_body(fm: FieldMap, start_ms: int, end_ms: int) -> Dict[str, Any]:
    """The customer labels of the week's Sysmon events."""
    return _base(
        [_week_filter(fm, start_ms, end_ms), _channel_filter(fm)],
        {"labels": {"terms": {"field": fm.label, "size": settings.STAGE0_LABELS_SIZE}}},
    )


def parse_stage0(response: Dict[str, Any]) -> Tuple[Dict[str, int], bool]:
    """({label: events}, whether labels were left out past the size)."""
    agg = (response.get("aggregations") or {}).get("labels") or {}
    labels: Dict[str, int] = {}
    for bucket in agg.get("buckets") or []:
        key = bucket.get("key")
        if isinstance(key, str):
            labels[key] = labels.get(key, 0) + int(bucket.get("doc_count") or 0)
    return labels, bool(agg.get("sum_other_doc_count"))


def _level_filter(fm: FieldMap, level_max: int) -> Dict[str, Any]:
    return {"terms": {fm.level: list(range(0, level_max + 1))}}


def stage1_body(fm: FieldMap, labels: List[str], start_ms: int, end_ms: int, level_max: int) -> Dict[str, Any]:
    """The customer's report endpoints (every Sysmon event of the week, any level), its computers' names (when mapped:
    what its host names and own domains are learned from, never sent), and its quiet events' top (event ID, actor)
    pairs, each with its endpoints."""
    actor_aggs: Dict[str, Any] = {}
    for actor in ("Image", "SourceImage", "ImageLoaded"):
        name = fm.ed(actor)
        if name:
            actor_aggs[f"actor_{actor}"] = {
                "terms": {"field": name, "size": settings.STAGE1_ACTOR_SIZE},
                "aggs": {"endpoints": {"cardinality": {"field": fm.agent, "precision_threshold": settings.PRECISION_LEAF}}},
            }
    by_event: Dict[str, Any] = {"terms": {"field": fm.event_id, "size": len(EVENT_IDS)}}
    if actor_aggs:
        by_event["aggs"] = actor_aggs
    aggs: Dict[str, Any] = {"endpoints": {"cardinality": {"field": fm.agent, "precision_threshold": settings.PRECISION_REPORT}}}
    if fm.computer:
        aggs["computers"] = {"terms": {"field": fm.computer, "size": settings.STAGE1_COMPUTERS_SIZE}}
    return _base(
        [_week_filter(fm, start_ms, end_ms), _channel_filter(fm), {"terms": {fm.label: list(labels)}}],
        {
            **aggs,
            "quiet": {
                "filter": {
                    "bool": {
                        "filter": [_level_filter(fm, level_max), {"terms": {fm.event_id: [str(e) for e in EVENT_IDS]}}],
                    },
                },
                "aggs": {"by_event": by_event},
            },
        },
    )


@dataclass
class Pair:
    eid: int
    actor: str
    events: int
    endpoints: int


@dataclass
class Stage1:
    endpoints: int
    pairs: List[Pair] = field(default_factory=list)
    # The customer's computers' names (the Windows event's Computer), when mapped
    computers: List[str] = field(default_factory=list)
    # The doc_count of the last returned bucket of each actor agg that left buckets out (its tail could have qualified)
    cut_tails: List[int] = field(default_factory=list)


def _int_key(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_stage1(response: Dict[str, Any]) -> Stage1:
    aggs = response.get("aggregations") or {}
    endpoints = int((aggs.get("endpoints") or {}).get("value") or 0)
    result = Stage1(endpoints=endpoints)
    for bucket in (aggs.get("computers") or {}).get("buckets") or []:
        key = bucket.get("key")
        if isinstance(key, str) and key.strip():
            result.computers.append(key)
    for event in ((aggs.get("quiet") or {}).get("by_event") or {}).get("buckets") or []:
        eid = _int_key(event.get("key"))
        if eid not in EVENT_PLAN:
            continue
        actor_agg = event.get(f"actor_{EVENT_PLAN[eid].actor}") or {}
        buckets = actor_agg.get("buckets") or []
        for bucket in buckets:
            key = bucket.get("key")
            if not isinstance(key, str):
                continue
            result.pairs.append(
                Pair(eid, key, int(bucket.get("doc_count") or 0), int((bucket.get("endpoints") or {}).get("value") or 0)),
            )
        if actor_agg.get("sum_other_doc_count") and buckets:
            result.cut_tails.append(int(buckets[-1].get("doc_count") or 0))
    return result


def select_pairs(pairs: Iterable[Pair], min_endpoints: int) -> Tuple[List[Pair], bool]:
    """The pairs worth a stage-2 query: seen on at least min_endpoints endpoints (a pair below it cannot yield a pattern
    that is sent), the most events first, at most PAIRS_PER_EVENT per event and PAIRS_TOTAL in all. Also whether
    qualifying pairs were left out."""
    qualifying = sorted((p for p in pairs if p.endpoints >= min_endpoints), key=lambda p: (-p.events, p.eid, p.actor))
    chosen: List[Pair] = []
    per_event: Dict[int, int] = {}
    left_out = False
    for pair in qualifying:
        if len(chosen) >= settings.PAIRS_TOTAL or per_event.get(pair.eid, 0) >= settings.PAIRS_PER_EVENT:
            left_out = True
            continue
        chosen.append(pair)
        per_event[pair.eid] = per_event.get(pair.eid, 0) + 1
    return chosen, left_out


def _leaf_aggs(fm: FieldMap, eid: int) -> Dict[str, Any]:
    plan = EVENT_PLAN[eid]
    aggs: Dict[str, Any] = {
        "endpoints": {"cardinality": {"field": fm.agent, "precision_threshold": settings.PRECISION_LEAF}},
        "days": {"date_histogram": {"field": fm.time, "fixed_interval": "1d", "time_zone": "UTC", "min_doc_count": 1}},
    }
    if fm.ed("RuleName"):
        aggs["rule_name"] = {"terms": {"field": fm.ed("RuleName"), "size": 2}}
    for name, size in plan.details:
        if fm.ed(name):
            aggs[f"d_{name}"] = {"terms": {"field": fm.ed(name), "size": size}}
    return aggs


def _leaf_buckets(leaf_aggs: Dict[str, Any]) -> int:
    """Buckets one leaf costs: its cardinality, at most 7 days, and every terms agg at its size."""
    total = 1
    for agg in leaf_aggs.values():
        if "date_histogram" in agg:
            total += 7
        elif "terms" in agg:
            total += agg["terms"]["size"]
    return total


def bucket_cost(actors: int, sizes: List[int], leaf: int) -> int:
    cost, width = 0, actors
    cost += width
    for size in sizes:
        width *= size
        cost += width
    return cost + width * leaf


def stage2_body(
    fm: FieldMap,
    labels: List[str],
    start_ms: int,
    end_ms: int,
    level_max: int,
    eid: int,
    actors: List[str],
) -> Dict[str, Any]:
    """The patterns of one event ID below the selected actors: the plan's nested terms, and per leaf its endpoints,
    days, rule names and detail values. The first nested size is halved until the worst case fits BUCKET_BUDGET."""
    plan = EVENT_PLAN[eid]
    leaf = _leaf_aggs(fm, eid)
    sizes = [nest.size for nest in plan.nests]
    while sizes and sizes[0] > 1 and bucket_cost(len(actors), sizes, _leaf_buckets(leaf)) > settings.BUCKET_BUDGET:
        sizes[0] = max(1, sizes[0] // 2)
    inner: Dict[str, Any] = leaf
    for depth in range(len(plan.nests) - 1, -1, -1):
        nest = plan.nests[depth]
        terms: Dict[str, Any] = {"field": fm.ed(nest.name), "size": sizes[depth]}
        if nest.missing:
            terms["missing"] = MISSING
        inner = {f"k{depth + 1}": {"terms": terms, "aggs": inner}}
    actor_field = fm.ed(plan.actor)
    return _base(
        [
            _week_filter(fm, start_ms, end_ms),
            _channel_filter(fm),
            {"terms": {fm.label: list(labels)}},
            _level_filter(fm, level_max),
            {"term": {fm.event_id: str(eid)}},
            {"terms": {actor_field: list(actors)}},
        ],
        {"actor": {"terms": {"field": actor_field, "size": len(actors)}, "aggs": inner}},
    )


@dataclass
class RawPattern:
    """One stage-2 leaf, raw (values as indexed, before any redaction)."""

    eid: int
    key: Dict[str, str]
    events: int
    endpoints: int
    days: int
    # Detail name -> the values that together cover every event of the leaf (None: they do not, or none)
    details: Dict[str, Optional[List[str]]] = field(default_factory=dict)
    rule_names: Optional[List[str]] = None
    # Every account value seen in the leaf's user details, covering or not (names to redact are learned from them)
    accounts: List[str] = field(default_factory=list)


def _covering(agg: Optional[Dict[str, Any]], doc_count: int) -> Optional[List[str]]:
    """The values of a terms agg when they cover every event of the leaf (nothing left out, nothing missing)."""
    if not isinstance(agg, dict):
        return None
    buckets = agg.get("buckets") or []
    if not buckets or agg.get("sum_other_doc_count"):
        return None
    values = [b.get("key") for b in buckets]
    if any(not isinstance(v, (str, int)) or isinstance(v, bool) for v in values):
        return None
    if sum(int(b.get("doc_count") or 0) for b in buckets) != doc_count:
        return None
    return [str(v) for v in values]


def _days_mask(agg: Optional[Dict[str, Any]]) -> int:
    mask = 0
    for bucket in (agg or {}).get("buckets") or []:
        if not bucket.get("doc_count"):
            continue
        key = bucket.get("key")
        if not isinstance(key, (int, float)) or isinstance(key, bool):
            continue
        day = datetime.fromtimestamp(key / 1000, tz=timezone.utc)
        mask |= 1 << day.weekday()
    return mask


def parse_stage2(response: Dict[str, Any], eid: int) -> Tuple[List[RawPattern], List[int]]:
    """(the leaves, the doc_count of the last bucket of each nested terms agg that left buckets out)."""
    plan = EVENT_PLAN[eid]
    leaves: List[RawPattern] = []
    cut_tails: List[int] = []

    def walk(agg: Dict[str, Any], depth: int, key: Dict[str, str]) -> None:
        buckets = agg.get("buckets") or []
        if agg.get("sum_other_doc_count") and buckets:
            cut_tails.append(int(buckets[-1].get("doc_count") or 0))
        name = plan.actor if depth == 0 else plan.nests[depth - 1].name
        for bucket in buckets:
            value = bucket.get("key")
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                continue
            here = {**key, name: str(value)}
            if depth < len(plan.nests):
                child = bucket.get(f"k{depth + 1}")
                if isinstance(child, dict):
                    walk(child, depth + 1, here)
                continue
            doc_count = int(bucket.get("doc_count") or 0)
            if doc_count < 1:
                continue
            details = {detail: _covering(bucket.get(f"d_{detail}"), doc_count) for detail, _ in plan.details}
            accounts = [
                str(b.get("key"))
                for detail in USER_DETAILS
                for b in ((bucket.get(f"d_{detail}") or {}).get("buckets") or [])
                if isinstance(b.get("key"), str)
            ]
            leaves.append(
                RawPattern(
                    eid=eid,
                    key=here,
                    events=doc_count,
                    endpoints=int((bucket.get("endpoints") or {}).get("value") or 0),
                    days=_days_mask(bucket.get("days")),
                    details=details,
                    rule_names=_covering(bucket.get("rule_name"), doc_count),
                    accounts=accounts,
                ),
            )

    actor = (response.get("aggregations") or {}).get("actor")
    if isinstance(actor, dict):
        walk(actor, 0, {})
    return leaves, cut_tails


def merge_shapes(patterns: List[RawPattern]) -> List[RawPattern]:
    """Merge leaves of the same raw key found in both shapes (a customer moving from one pipeline to the other, or two
    pipelines ingesting the same events at once): days ORed, a detail's covering values united (both must cover), and
    events and endpoints the larger of the two, never their sum. The same endpoints (and, with two pipelines, the same
    events) may be in both shapes, so a sum could count them twice and lift a pattern over the endpoints floor; the
    larger count is a lower bound either way."""
    merged: Dict[Tuple[int, Tuple[Tuple[str, str], ...]], RawPattern] = {}
    for p in patterns:
        k = (p.eid, tuple(sorted(p.key.items())))
        if k not in merged:
            merged[k] = RawPattern(p.eid, dict(p.key), p.events, p.endpoints, p.days, dict(p.details), p.rule_names, list(p.accounts))
            continue
        m = merged[k]
        m.events = max(m.events, p.events)
        m.endpoints = max(m.endpoints, p.endpoints)
        m.days |= p.days
        m.accounts.extend(p.accounts)
        for name in set(m.details) | set(p.details):
            a, b = m.details.get(name), p.details.get(name)
            m.details[name] = sorted(set(a) | set(b)) if a is not None and b is not None else None
        m.rule_names = sorted(set(m.rule_names) | set(p.rule_names)) if m.rule_names is not None and p.rule_names is not None else None
    return list(merged.values())
