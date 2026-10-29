"""
In-memory cache of per-rule firing counts from the Wazuh indexer.

Why this exists:
The catalog wants to surface "how often has this rule fired in the last
7d/30d?" for every Wazuh rule. The naive way (one ES query per rule, per
request, per user) would crush the indexer. Instead we do **one** terms
aggregation over the alerts indices, cache the result, and serve every
per-rule lookup from the dict.

Cost: one ``_cat/indices`` call, one ``_field_caps`` call and one ``search``
request to the Wazuh indexer every ``CACHE_TTL_MINUTES`` minutes (15 by
default). The aggregation is a date-filtered ``terms`` over the rule ID with
a sub-aggregation for the 7d sub-window. On a small cluster it returns in
well under a second; on one with a few hundred alert indices it was measured
at ~29s (#1319), which is why it has its own time budget.

Time budget (#1319):
The shared indexer client gives up after 15s, which a 30-day aggregation
over hundreds of indices does not fit in. Every firing-stats search passes
its own ``request_timeout`` (``FIRING_STATS_TIMEOUT_SECONDS``, default 120)
and the same budget, a few seconds shorter, as the search body's ``timeout``
so the indexer stops collecting before the client gives up. A search the
client abandons anyway is cancelled through the task API by its
``X-Opaque-Id``: an abandoned aggregation otherwise keeps running on the
cluster, and one was left behind on every refresh until other dashboards on
the same indexer started timing out. A search that times out on either side
is a failure, never a partial answer: undercounted hits would put live rules
under "Dead". Nothing tries another field after a timeout, since it would
cost the same. Every search runs one at a time across the global refresh
and the per-customer slices.

Index target (why not just ``wazuh-alerts-*``):
In a default Wazuh install, all alerts live in ``wazuh-alerts-*``. In
real SOCFortress deployments they don't — different integrations write to
different indices (``office365-<customer>``, ``crowdstrike-<customer>``,
``carbonblack-<customer>``, ``huntress_<customer>``, ad-hoc ``newest-*``
test indices, …). Hardcoding ``wazuh-alerts-*`` misses all of them. The
default is therefore every index minus the ones that are definitely *not*
alert indices (``ALERT_INDEX_PATTERN``), which ES resolves server-side.
``FIRING_STATS_INDEX_PATTERN`` replaces it for a deployment that knows where
its alerts are and doesn't want firewall indices scanned.

Field-name choice:
The rule ID lives under ``rule.id`` (Wazuh's own template) or ``rule_id``
(Graylog's flat mapping). One ``_field_caps`` call says which of them are
mapped and aggregatable before any aggregation runs, so a field that isn't
there costs nothing. The winning field is tried first on the next refresh.
``id`` used to be a third fallback; on Graylog-fed clusters it is a
high-cardinality document id in non-Wazuh indices, so a 30-day ``terms``
on it was the most expensive query of all and never useful (#1319).

No DB writes, no schema changes, no Alembic migrations — pure read-only
aggregation against the live indices plus an in-memory dict on the CoPilot
side.
"""

import asyncio
import os
import re
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from elasticsearch7.exceptions import ConnectionTimeout
from elasticsearch7.exceptions import RequestError
from loguru import logger

from app.integrations.copilot_searches.services.cache_support import (
    BackgroundRefreshMixin,
)

# 15-min TTL strikes a balance: fresh enough that the dashboard reflects
# real-time tuning, cheap enough that the indexer barely notices. A failed
# refresh waits the same TTL before it is tried again.
CACHE_TTL_MINUTES = 15

# ``FIRING_STATS_TIMEOUT_SECONDS``: how long one aggregation may take.
DEFAULT_TIMEOUT_SECONDS = 120
MIN_TIMEOUT_SECONDS = 10
MAX_TIMEOUT_SECONDS = 600
# The search body's ``timeout`` is this much shorter than the client's, so the
# indexer answers ``timed_out`` before the client stops waiting.
SERVER_TIMEOUT_MARGIN_SECONDS = 5
# Metadata calls (field caps, finding and cancelling a task) are cheap.
METADATA_TIMEOUT_SECONDS = 30

# Per-customer slices kept in memory (least recently asked for dropped first).
CUSTOMER_CACHE_SIZE = 16

# ES-native index pattern with exclusions. We pass this as a single short
# string (~150 bytes) to ``client.search(index=...)``, which lets ES resolve
# it server-side. The previous approach of enumerating indices via
# ``_cat/indices`` and passing the list client-side blew up at scale —
# 1582 indices in a single URL crosses the 4096-byte HTTP line limit
# (``too_long_http_line_exception``).
#
# Exclusion rationale:
# - ``.*`` / ``_*``: Kibana / OpenSearch / Security plugin internals.
# - ``wazuh-monitoring-*`` / ``wazuh-statistics-*`` / ``wazuh-states-*`` /
#   ``wazuh-vulnerabilities-*``: Wazuh's own internal indices. Carry rule.id
#   for system/control events with parent-template rule IDs (2 = firewall,
#   3 = ids, 4 = web-log) that never fire on real alerts but produce massive
#   fake hit counts. ``wazuh-vulnerabilities-*`` is the agent vulnerability
#   state index, also not alert data.
# - ``security-auditlog-*``: OpenSearch Security plugin's audit log.
#
# The integer-coerce filter in ``_coerce_rule_id`` is the second line of
# defense — even if a vendor index sneaks in, non-Wazuh rule IDs (string
# identifiers like ``"Office365_FailedLogin"``) get silently dropped.
ALERT_INDEX_PATTERN = (
    "*" ",-.*" ",-_*" ",-wazuh-monitoring-*" ",-wazuh-statistics-*" ",-wazuh-states-*" ",-wazuh-vulnerabilities-*" ",-security-auditlog-*"
)

# Longest ``FIRING_STATS_INDEX_PATTERN`` accepted: it travels in the URL path,
# and the indexer refuses a request line over 4096 bytes.
MAX_INDEX_PATTERN_LENGTH = 1000

# Equivalent regex list — used only by the introspection helper
# ``_discover_alert_indices`` to populate ``resolved_indices`` for
# logging/debugging. The search itself never uses these; ES handles the
# pattern above natively.
EXCLUDE_PATTERNS = [
    re.compile(r"^\."),
    re.compile(r"^_"),
    re.compile(r"^wazuh-monitoring"),
    re.compile(r"^wazuh-statistics"),
    re.compile(r"^wazuh-states"),
    re.compile(r"^wazuh-vulnerabilities"),
    re.compile(r"security-auditlog"),
]

# Where the rule ID may live, in order of preference. ``_field_caps`` narrows
# this to the ones actually mapped before anything is aggregated.
RULE_ID_FIELD_OPTIONS = ["rule.id", "rule_id"]

# Where the customer code may live: Graylog's flat convention, which
# SOCFortress pipelines produce, and the nested Wazuh-vanilla shape. One
# query matches either, so a slice costs one aggregation, not one per shape.
CUSTOMER_FIELD_OPTIONS = ["agent_labels_customer", "agent.labels.customer"]


def firing_stats_timeout_seconds() -> int:
    """``FIRING_STATS_TIMEOUT_SECONDS``, clamped; the default when unset or unreadable."""
    raw = os.getenv("FIRING_STATS_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        logger.warning(f"FIRING_STATS_TIMEOUT_SECONDS={raw!r} is not a whole number of seconds; using {DEFAULT_TIMEOUT_SECONDS}")
        return DEFAULT_TIMEOUT_SECONDS
    return max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, value))


def firing_stats_index_pattern() -> str:
    """``FIRING_STATS_INDEX_PATTERN``, or ``ALERT_INDEX_PATTERN`` when unset or unusable."""
    raw = os.getenv("FIRING_STATS_INDEX_PATTERN", "").strip()
    if not raw:
        return ALERT_INDEX_PATTERN
    if len(raw) > MAX_INDEX_PATTERN_LENGTH or any(ch.isspace() or ord(ch) < 32 for ch in raw) or not raw.strip(","):
        logger.warning("FIRING_STATS_INDEX_PATTERN is not a usable index pattern; using the default")
        return ALERT_INDEX_PATTERN
    return raw


def _timeout_reason(timeout: int) -> str:
    return (
        f"Counting rule hits did not finish within {timeout}s. "
        "Raise FIRING_STATS_TIMEOUT_SECONDS, or set FIRING_STATS_INDEX_PATTERN to the indices that hold alerts."
    )


NO_RULE_FIELD_REASON = "No rule ID field (rule.id or rule_id) is mapped in the alert indices."


class AggregationTimedOut(Exception):
    """The indexer, or the client waiting for it, ran out of time."""


@dataclass
class _Outcome:
    stats: Dict[int, Dict[str, Any]] = dataclass_field(default_factory=dict)
    field: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CustomerFiringStats:
    """One customer's slice: ``ready`` (``stats`` may be empty: no hits), ``loading`` or ``error``."""

    status: str
    stats: Dict[int, Dict[str, Any]] = dataclass_field(default_factory=dict)
    error: Optional[str] = None
    fetched_at: Optional[datetime] = None


# One heavy search at a time, across the global refresh and every customer
# slice: the cluster serves other dashboards too (#1319). Bound to the running
# loop, so a new loop (tests, a restart of the app's loop) gets a fresh one.
_heavy_slot: Optional[asyncio.Semaphore] = None
_heavy_slot_loop: Optional[asyncio.AbstractEventLoop] = None


def _heavy_query_slot() -> asyncio.Semaphore:
    global _heavy_slot, _heavy_slot_loop
    loop = asyncio.get_running_loop()
    if _heavy_slot is None or _heavy_slot_loop is not loop:
        _heavy_slot = asyncio.Semaphore(1)
        _heavy_slot_loop = loop
    return _heavy_slot


class WazuhFiringStatsCache(BackgroundRefreshMixin):
    """
    Per-rule firing-count cache, keyed by integer rule ID.

    Returns a small dict per rule: ``{"hits_30d": int, "hits_7d": int}``.
    Rules with zero hits over the 30d window are deliberately omitted from
    the dict — callers should treat "missing" as "0 hits" rather than
    "data unavailable". ``has_stats`` distinguishes those two states
    explicitly.
    """

    def __init__(self) -> None:
        # rule_id (int) -> {"hits_30d": int, "hits_7d": int}
        self._stats: Dict[int, Dict[str, int]] = {}
        self._last_refresh: Optional[datetime] = None
        self._unavailable_reason: Optional[str] = None
        # Field path that worked last time; tried first on next refresh.
        self._winning_field: Optional[str] = None
        # Indices discovered on last refresh — kept for introspection so
        # operators can see "which indices did we actually aggregate over?"
        # without having to spelunk through logs.
        self._resolved_indices: List[str] = []
        self._lock = asyncio.Lock()
        # Per-customer slices, least recently asked for first, and the
        # refresh in flight for each.
        self._customer_slices: "OrderedDict[str, CustomerFiringStats]" = OrderedDict()
        self._customer_tasks: Dict[str, asyncio.Task] = {}

    # ---- introspection ----------------------------------------------------

    @property
    def is_stale(self) -> bool:
        if self._last_refresh is None:
            return True
        return (datetime.utcnow() - self._last_refresh) > timedelta(minutes=CACHE_TTL_MINUTES)

    @property
    def last_refresh(self) -> Optional[datetime]:
        return self._last_refresh

    @property
    def is_available(self) -> bool:
        return self._unavailable_reason is None

    @property
    def is_loaded(self) -> bool:
        """True once a refresh has finished, whatever its outcome."""
        return self._last_refresh is not None

    @property
    def has_stats(self) -> bool:
        """True when the counts can be shown: loaded, and the last refresh worked.

        Before the first refresh finishes the dict is empty, and showing it
        would read as "nothing has ever fired".
        """
        return self.is_loaded and self.is_available

    @property
    def unavailable_reason(self) -> Optional[str]:
        return self._unavailable_reason

    @property
    def resolved_indices(self) -> List[str]:
        """Indices that the last refresh actually aggregated across."""
        return list(self._resolved_indices)

    # ---- loading ----------------------------------------------------------

    async def ensure_loaded(self) -> None:
        """Lazy-load on first access; refresh on TTL expiry. Never raises."""
        if self.is_stale:
            await self.refresh()

    async def refresh(self) -> int:
        """
        Fire one terms-aggregation against the alerts indices and rebuild the
        per-rule stats dict. Returns the number of rules with at least one
        hit in the 30d window.

        Never raises — failures are captured in ``unavailable_reason`` and
        the existing cached snapshot is left in place.
        """
        # Local import to avoid pulling the indexer client at module-import
        # time on deployments where the indexer connector isn't usable.
        from app.connectors.wazuh_indexer.utils.universal import (
            create_wazuh_indexer_client_async,
        )

        async with self._lock:
            logger.info("Refreshing Wazuh firing-stats cache from the indexer…")
            timeout = firing_stats_timeout_seconds()
            index = firing_stats_index_pattern()

            try:
                client = await create_wazuh_indexer_client_async()
            except Exception as exc:  # noqa: BLE001
                return self._fail(_short_reason(exc))

            try:
                # Debug aid only: which concrete indices the pattern expands
                # to. Failure is non-fatal — the search still runs on the
                # pattern.
                self._resolved_indices = await _discover_alert_indices(client, index)
                logger.debug(
                    f"Firing-stats aggregating across {len(self._resolved_indices)} concrete index target(s); "
                    f"first few: {self._resolved_indices[:5]}",
                )
                fields = await _rule_field_candidates(client, index, self._winning_field)
                if not fields:
                    return self._fail(NO_RULE_FIELD_REASON)
                async with _heavy_query_slot():
                    outcome = await _aggregate_first_field(client, index, fields, timeout)
            finally:
                await _close(client)

            if outcome.field is None:
                # No field worked, or all returned empty. Treat as
                # "unavailable" so the UI doesn't render a useless "0 hits"
                # column for every rule when really we just can't tell.
                return self._fail(outcome.error or "No rule ID field returned hits in the alert indices.")

            self._stats = outcome.stats
            self._winning_field = outcome.field
            self._unavailable_reason = None
            self._last_refresh = datetime.utcnow()
            logger.info(
                f"Loaded firing stats for {len(self._stats)} rule(s) using field '{outcome.field}'",
            )
            return len(self._stats)

    def _fail(self, reason: str) -> int:
        self._unavailable_reason = reason
        self._last_refresh = datetime.utcnow()
        logger.warning(f"Wazuh firing stats unavailable: {reason}")
        return len(self._stats)

    # ---- per-customer slices ------------------------------------------------

    def customer_stats(self, customer_code: str) -> CustomerFiringStats:
        """
        One customer's slice, without waiting for the indexer.

        A slice is one more aggregation as heavy as the global one, so a
        request never runs it: the first ask starts it in the background and
        answers ``loading``, and the UI asks again until it lands. A slice is
        kept ``CACHE_TTL_MINUTES``; an older one is still served while its
        refresh runs. A failed slice waits the same TTL before it is retried.
        """
        entry = self._customer_slices.get(customer_code)
        if entry is not None:
            self._customer_slices.move_to_end(customer_code)
        fresh = (
            entry is not None
            and entry.fetched_at is not None
            and datetime.utcnow() - entry.fetched_at <= timedelta(minutes=CACHE_TTL_MINUTES)
        )
        if not fresh:
            self._schedule_customer_refresh(customer_code)
        if entry is None:
            return CustomerFiringStats(status="loading")
        return entry

    def _schedule_customer_refresh(self, customer_code: str) -> None:
        task = self._customer_tasks.get(customer_code)
        if task is not None and not task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._customer_tasks[customer_code] = loop.create_task(self._refresh_customer(customer_code))

    async def _refresh_customer(self, customer_code: str) -> None:
        try:
            result = await fetch_firing_stats_for_customer(customer_code)
            self._customer_slices[customer_code] = result
            self._customer_slices.move_to_end(customer_code)
            while len(self._customer_slices) > CUSTOMER_CACHE_SIZE:
                self._customer_slices.popitem(last=False)
        except Exception as exc:  # noqa: BLE001 — a background task must never escape
            logger.warning(f"Per-customer firing stats failed: {exc}")
        finally:
            self._customer_tasks.pop(customer_code, None)

    # ---- accessors --------------------------------------------------------

    def get(self, rule_id: int) -> Dict[str, Any]:
        """
        Return ``{"hits_30d": int, "hits_7d": int, "last_seen": str | None}``
        for ``rule_id``.

        Missing rule IDs return zero counts + None last_seen — the rule
        exists in the cache but simply hasn't fired in the 30d window.
        Callers that need to distinguish "0 hits" from "stats unavailable"
        should check ``has_stats`` separately.
        """
        return self._stats.get(
            rule_id,
            {"hits_30d": 0, "hits_7d": 0, "last_seen": None},
        )


# ---------------------------------------------------------------------------
# Per-customer firing stats
# ---------------------------------------------------------------------------


async def fetch_firing_stats_for_customer(customer_code: str) -> CustomerFiringStats:
    """
    Run the firing-stats aggregation filtered to a single customer code.

    Called in the background by ``WazuhFiringStatsCache.customer_stats``,
    never from a request. Kept per customer for ``CACHE_TTL_MINUTES``, at
    most ``CUSTOMER_CACHE_SIZE`` customers, so a deployment with dozens of
    customers holds only the slices someone is looking at.

    Never raises. Answers ``ready`` with an empty dict when the customer has
    no alerts in the window, and ``error`` with a reason when the indexer
    could not answer — which the UI shows instead of a column of zeros.
    """
    from app.connectors.wazuh_indexer.utils.universal import (
        create_wazuh_indexer_client_async,
    )

    if not customer_code or not customer_code.strip():
        return CustomerFiringStats(status="ready", fetched_at=datetime.utcnow())

    timeout = firing_stats_timeout_seconds()
    index = firing_stats_index_pattern()

    try:
        client = await create_wazuh_indexer_client_async()
    except Exception as exc:  # noqa: BLE001
        reason = _short_reason(exc)
        logger.warning(f"Per-customer firing stats: indexer unavailable ({reason})")
        return CustomerFiringStats(status="error", error=reason, fetched_at=datetime.utcnow())

    try:
        # The global refresh's field when it has one, saving a field_caps call.
        winner = wazuh_firing_stats_cache._winning_field
        fields = [winner] if winner else await _rule_field_candidates(client, index, None)
        if not fields:
            return CustomerFiringStats(status="error", error=NO_RULE_FIELD_REASON, fetched_at=datetime.utcnow())
        customer_filter = {
            "bool": {
                "should": [{"term": {f: customer_code}} for f in CUSTOMER_FIELD_OPTIONS],
                "minimum_should_match": 1,
            },
        }
        async with _heavy_query_slot():
            outcome = await _aggregate_first_field(client, index, fields, timeout, extra_filter=customer_filter)
    finally:
        await _close(client)

    if outcome.field is None and outcome.error:
        logger.warning(f"Per-customer firing stats failed: {outcome.error}")
        return CustomerFiringStats(status="error", error=outcome.error, fetched_at=datetime.utcnow())

    logger.debug(f"Per-customer firing stats: {len(outcome.stats)} rules for customer {customer_code!r}")
    return CustomerFiringStats(status="ready", stats=outcome.stats, fetched_at=datetime.utcnow())


# ---------------------------------------------------------------------------
# Indexer calls
# ---------------------------------------------------------------------------


async def _aggregate_first_field(
    client: Any,
    index: str,
    fields: List[str],
    timeout: int,
    extra_filter: Optional[Dict[str, Any]] = None,
) -> _Outcome:
    """
    Aggregate on each field in turn until one returns buckets.

    A 4xx (the field can't be aggregated in some index) moves on to the next
    field. A timeout or any other failure stops: the next field would cost as
    much, or the indexer is in trouble.
    """
    last_error: Optional[str] = None
    for field in fields:
        body = _build_firing_stats_query(field)
        if extra_filter is not None:
            body["query"]["bool"]["filter"].append(extra_filter)
        try:
            response = await _aggregate(client, index, body, timeout)
        except AggregationTimedOut:
            return _Outcome(error=_timeout_reason(timeout))
        except RequestError as exc:
            # The .info payload has the human message (see CLAUDE.md "Things that bite").
            last_error = f"{field}: {str(exc.info)[:120]}"
            logger.debug(f"Firing-stats field '{field}' rejected: {last_error}")
            continue
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Firing-stats field '{field}' errored: {exc}")
            return _Outcome(error=_short_reason(exc))

        stats = _parse_buckets(response)
        if stats:
            return _Outcome(stats=stats, field=field)
    return _Outcome(error=last_error)


async def _aggregate(client: Any, index: str, body: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """
    One firing-stats search within ``timeout`` seconds, on both sides.

    Raises ``AggregationTimedOut`` when the indexer reports ``timed_out``
    (its per-shard budget ran out, so the counts would be partial) or the
    client stops waiting; in the second case the search is cancelled first.
    """
    opaque_id = f"copilot-firing-stats-{uuid.uuid4().hex}"
    body = {**body, "timeout": f"{max(1, timeout - SERVER_TIMEOUT_MARGIN_SECONDS)}s"}
    try:
        # ``ignore_unavailable`` swallows per-index permission / missing-index
        # errors so one bad index doesn't fail the whole aggregation.
        # ``allow_no_indices`` likewise stops the request from 4xx-ing when
        # the pattern matches zero indices (fresh deployment, etc.).
        response = await client.search(
            index=index,
            body=body,
            ignore_unavailable=True,
            allow_no_indices=True,
            request_timeout=timeout,
            opaque_id=opaque_id,
        )
    except ConnectionTimeout:
        await _cancel_search(client, opaque_id)
        raise AggregationTimedOut()
    if response.get("timed_out"):
        raise AggregationTimedOut()
    shards = response.get("_shards") or {}
    if shards.get("failed"):
        logger.warning(f"Firing-stats aggregation: {shards.get('failed')} of {shards.get('total')} shard(s) failed")
    return response


async def _cancel_search(client: Any, opaque_id: str) -> None:
    """
    Cancel the search the client gave up on, found by its ``X-Opaque-Id``.

    Best effort: without it the indexer keeps aggregating for nobody, and
    each refresh used to leave one or two of those behind (#1319).
    """
    try:
        listing = await client.tasks.list(
            actions="indices:data/read/search",
            detailed=True,
            request_timeout=METADATA_TIMEOUT_SECONDS,
        )
        for node in ((listing or {}).get("nodes") or {}).values():
            for task_id, task in ((node or {}).get("tasks") or {}).items():
                headers = (task or {}).get("headers") or {}
                if any(str(k).lower() == "x-opaque-id" and v == opaque_id for k, v in headers.items()):
                    await client.tasks.cancel(task_id=task_id, request_timeout=METADATA_TIMEOUT_SECONDS)
                    logger.info(f"Cancelled abandoned firing-stats search {task_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not cancel an abandoned firing-stats search: {exc}")


async def _rule_field_candidates(client: Any, index: str, preferred: Optional[str]) -> List[str]:
    """
    The rule-ID fields worth aggregating on, ``preferred`` first.

    Only fields ``_field_caps`` reports as mapped and aggregatable somewhere
    in ``index``. When field caps can't be read, every option, so a cluster
    that refuses the call still gets counts.
    """
    try:
        response = await client.field_caps(
            index=index,
            fields=",".join(RULE_ID_FIELD_OPTIONS),
            ignore_unavailable=True,
            allow_no_indices=True,
            request_timeout=METADATA_TIMEOUT_SECONDS,
        )
        caps = (response or {}).get("fields") or {}
        fields = [
            f
            for f in RULE_ID_FIELD_OPTIONS
            if any(isinstance(spec, dict) and spec.get("aggregatable") for spec in (caps.get(f) or {}).values())
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Firing-stats field discovery failed, trying every rule ID field: {exc}")
        fields = list(RULE_ID_FIELD_OPTIONS)
    if preferred in fields:
        fields.remove(preferred)
        fields.insert(0, preferred)
    return fields


async def _close(client: Any) -> None:
    try:
        await client.close()
    except Exception:  # noqa: BLE001
        pass


def _parse_buckets(response: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    stats: Dict[int, Dict[str, Any]] = {}
    for bucket in response.get("aggregations", {}).get("by_rule", {}).get("buckets", []):
        rule_id = _coerce_rule_id(bucket.get("key"))
        if rule_id is None:
            continue
        # ``max(timestamp)`` comes back as ``{"value": <epoch millis>,
        # "value_as_string": "<ISO>"}``; the ISO string goes straight to the UI.
        stats[rule_id] = {
            "hits_30d": int(bucket.get("doc_count") or 0),
            "hits_7d": int((bucket.get("last_7d") or {}).get("doc_count") or 0),
            "last_seen": (bucket.get("last_seen") or {}).get("value_as_string"),
        }
    return stats


def _build_firing_stats_query(field: str) -> Dict[str, Any]:
    """
    One query gets us 30d totals + 7d sub-totals in a single round-trip.

    The outer ``terms`` agg buckets the last 30 days by rule ID; the nested
    ``last_7d`` filter inside each bucket counts how many of those hits
    fell in the most recent week. Painless-free, fast, and the result is
    just a list of buckets — no docs returned (``size: 0``).
    """
    return {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"timestamp": {"gte": "now-30d"}}},
                    {"exists": {"field": field}},
                ],
            },
        },
        "aggs": {
            "by_rule": {
                # 50000 is the ES "terms" agg's recommended ceiling for a
                # single query; Wazuh ships ~3-5k rules so we'll never come
                # close. We just don't want a silent truncation.
                "terms": {"field": field, "size": 50000, "order": {"_count": "desc"}},
                "aggs": {
                    "last_7d": {
                        "filter": {"range": {"timestamp": {"gte": "now-7d"}}},
                    },
                    # max(timestamp) gives us "when did this rule last fire?"
                    # for free — same query, same scan, ES returns it as both
                    # epoch-millis and an ISO string. We thread the ISO form
                    # through to the UI so it can render relative time
                    # ("2 minutes ago", "26 days ago") without parsing.
                    "last_seen": {
                        "max": {"field": "timestamp"},
                    },
                },
            },
        },
    }


async def _discover_alert_indices(client: Any, index: str = ALERT_INDEX_PATTERN) -> List[str]:
    """
    The concrete indices ``index`` expands to, minus anything that is
    definitely not an alert index. For the debug log only — the search
    itself runs on the pattern. ``[]`` on any failure.

    Why including a vendor index that isn't Wazuh-alert shaped is safe:

    - The aggregation's ``exists`` filter on the rule-ID field drops
      documents that don't carry one.
    - ``_coerce_rule_id`` drops bucket keys that aren't integer-parseable —
      vendor-native rule identifiers like ``"Office365_FailedLogin"``
      don't pollute the Wazuh rule cache.
    """
    try:
        # ``h="index"`` restricts the columns to keep the response small.
        cat_response = await client.cat.indices(index=index, format="json", h="index", request_timeout=METADATA_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Firing-stats index discovery failed: {exc}")
        return []

    if not isinstance(cat_response, list):
        # Some clients return the raw HTTP response object instead of the
        # parsed body — defend against shape drift.
        logger.warning(
            f"Unexpected cat.indices response shape: {type(cat_response).__name__}",
        )
        return []

    kept: List[str] = []
    for item in cat_response:
        name = item.get("index") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name:
            continue
        if any(pat.search(name) for pat in EXCLUDE_PATTERNS):
            continue
        kept.append(name)

    return kept


def _coerce_rule_id(key: Any) -> Optional[int]:
    """
    Bucket keys come back as strings or ints depending on the field mapping
    (keyword vs long). Normalize to int; drop anything that doesn't parse.
    """
    if key is None:
        return None
    if isinstance(key, int):
        return key
    if isinstance(key, str):
        try:
            return int(key)
        except ValueError:
            return None
    return None


def _short_reason(exc: BaseException) -> str:
    """Mirror of the helper in wazuh_rules_cache — keep it local to avoid coupling."""
    raw = str(exc).strip() or exc.__class__.__name__
    lower = raw.lower()
    if "connection" in lower or "timed out" in lower or "timeout" in lower:
        return "Wazuh indexer is not reachable."
    if "401" in raw or "403" in raw or "unauthor" in lower:
        return "Wazuh indexer rejected the credentials."
    if "not configured" in lower or "not found" in lower:
        return "Wazuh indexer connector is not configured."
    return raw[:160] + ("…" if len(raw) > 160 else "")


# Module-level singleton — same pattern as the rules caches.
wazuh_firing_stats_cache = WazuhFiringStatsCache()
