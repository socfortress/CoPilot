"""
In-memory cache of per-rule firing counts from the Wazuh indexer.

Why this exists:
The catalog wants to surface "how often has this rule fired in the last
7d/30d?" for every Wazuh rule. The naive way (one ES query per rule, per
request, per user) would crush the indexer. Instead we do **one** terms
aggregation over the alerts indices, cache the result, and serve every
per-rule lookup from the dict.

Cost: one ``_cat/indices`` call + one ``search`` request to the Wazuh
indexer every ``CACHE_TTL_MINUTES`` minutes (15 by default). The
aggregation is a date-filtered ``terms`` over rule.id with a
sub-aggregation for the 7d sub-window. Even across hundreds of millions of
docs, this returns in well under a second.

Index auto-discovery (why we don't hardcode ``wazuh-alerts-*``):
In a default Wazuh install, all alerts live in ``wazuh-alerts-*``. In
real SOCFortress deployments they don't — different integrations write to
different indices (``office365-<customer>``, ``crowdstrike-<customer>``,
``carbonblack-<customer>``, ``huntress_<customer>``, ad-hoc ``newest-*``
test indices, …). Hardcoding ``wazuh-alerts-*`` misses all of them.
Maintaining a comma-separated env list is fragile — every new customer
integration would need a config bump.

Instead we list every index in the cluster on each refresh, filter out
indices that are definitely *not* alert indices (Wazuh's internal
``monitoring/statistics/states`` plus Kibana/OpenSearch system indices),
and aggregate across whatever's left. The aggregation's
``exists`` filter on the rule-ID field naturally drops indices that don't
carry one, and ``_coerce_rule_id`` drops bucket keys that aren't
integer-parseable — so vendor indices with their own non-Wazuh rule IDs
(e.g. ``"Office365_FailedLogin"``) don't pollute the cache.

Field-name fallback:
Wazuh's indexer schema varies across versions and shipping configurations.
The rule ID may live under ``rule.id`` (object mapping), ``rule_id`` (flat
mapping), or just ``id`` (older schemas). We try them in that order, taking
the first one that returns non-empty buckets — same fallback pattern used
in ``app/connectors/wazuh_manager/services/mitre.py``.

No DB writes, no schema changes, no Alembic migrations, no env var —
pure read-only aggregation against the live indices plus an in-memory
dict on the CoPilot side.
"""

import asyncio
import re
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from elasticsearch7.exceptions import RequestError
from loguru import logger

# 15-min TTL strikes a balance: fresh enough that the dashboard reflects
# real-time tuning, cheap enough that the indexer barely notices.
CACHE_TTL_MINUTES = 15

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

# Try these field paths in order. First one that yields non-empty buckets
# wins and is cached for subsequent refreshes (avoids retrying the misses
# on every refresh).
RULE_ID_FIELD_OPTIONS = ["rule.id", "rule_id", "id"]


class WazuhFiringStatsCache:
    """
    Per-rule firing-count cache, keyed by integer rule ID.

    Returns a small dict per rule: ``{"hits_30d": int, "hits_7d": int}``.
    Rules with zero hits over the 30d window are deliberately omitted from
    the dict — callers should treat "missing" as "0 hits" rather than
    "data unavailable". The cache's ``is_available`` flag distinguishes
    those two states explicitly.
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
        Fire one terms-aggregation against the alerts index and rebuild the
        per-rule stats dict. Returns the number of rules with at least one
        hit in the 30d window.

        Never raises — failures are captured in ``unavailable_reason`` and
        the existing cached snapshot is left in place. A transient indexer
        outage shouldn't blank the firing-count column.
        """
        # Local import to avoid pulling the indexer client at module-import
        # time on deployments where the indexer connector isn't usable.
        from app.connectors.wazuh_indexer.utils.universal import (
            create_wazuh_indexer_client_async,
        )

        async with self._lock:
            logger.info("Refreshing Wazuh firing-stats cache from the indexer…")

            try:
                client = await create_wazuh_indexer_client_async()
            except Exception as exc:  # noqa: BLE001
                self._unavailable_reason = _short_reason(exc)
                logger.warning(f"Wazuh indexer client unavailable: {self._unavailable_reason}")
                self._last_refresh = datetime.utcnow()
                return len(self._stats)

            # Always search via the single ES wildcard+exclusion pattern —
            # ES resolves it server-side, sub-millisecond, no HTTP line
            # limits to worry about. The cat-indices discovery call below is
            # only for the introspection / debug log so operators can see
            # WHICH concrete indices the pattern expanded to without having
            # to run the cat call themselves. Discovery failure is non-fatal
            # — the search still runs on the pattern.
            self._resolved_indices = await _discover_alert_indices(client)
            logger.debug(
                f"Firing-stats aggregating across {len(self._resolved_indices)} concrete index target(s); "
                f"first few: {self._resolved_indices[:5]}",
            )
            search_target = ALERT_INDEX_PATTERN

            # Try the winning field first (if we have one from a prior load),
            # then fall back through the canonical list. First field that
            # returns non-empty buckets wins.
            fields_to_try: List[str] = []
            if self._winning_field:
                fields_to_try.append(self._winning_field)
            for f in RULE_ID_FIELD_OPTIONS:
                if f not in fields_to_try:
                    fields_to_try.append(f)

            new_stats: Dict[int, Dict[str, int]] = {}
            winner: Optional[str] = None
            last_error: Optional[str] = None

            for field in fields_to_try:
                try:
                    body = _build_firing_stats_query(field)
                    # ``ignore_unavailable`` swallows per-index permission /
                    # missing-index errors so one bad index doesn't fail the
                    # whole aggregation. ``allow_no_indices`` likewise stops
                    # the request from 4xx-ing when the pattern matches
                    # zero indices (fresh deployment, etc.).
                    response = await client.search(
                        index=search_target,
                        body=body,
                        ignore_unavailable=True,
                        allow_no_indices=True,
                    )
                    buckets = response.get("aggregations", {}).get("by_rule", {}).get("buckets", [])
                    if not buckets:
                        # Empty buckets = field exists but no docs, OR field
                        # doesn't exist. Either way, try the next one.
                        continue

                    for bucket in buckets:
                        rule_id = _coerce_rule_id(bucket.get("key"))
                        if rule_id is None:
                            continue
                        hits_30d = int(bucket.get("doc_count") or 0)
                        hits_7d = int(
                            bucket.get("last_7d", {}).get("doc_count") or 0,
                        )
                        # ``max(timestamp)`` bucket comes back as
                        # ``{"value": 1700000000000.0, "value_as_string": "..."}``
                        # (epoch millis + ISO string). Prefer the ISO string
                        # for direct UI rendering; fall back to None if the
                        # bucket is missing (shouldn't happen but defensive).
                        last_seen_bucket = bucket.get("last_seen") or {}
                        last_seen = last_seen_bucket.get("value_as_string")
                        new_stats[rule_id] = {
                            "hits_30d": hits_30d,
                            "hits_7d": hits_7d,
                            "last_seen": last_seen,
                        }
                    winner = field
                    break
                except RequestError as re:
                    # Most common: field doesn't exist on the index — Wazuh
                    # versions differ. The .info payload has the human
                    # message (see CLAUDE.md "Things that bite").
                    last_error = f"{field}: {str(re.info)[:120]}"
                    logger.debug(f"Firing-stats field '{field}' rejected: {last_error}")
                    continue
                except Exception as exc:  # noqa: BLE001
                    last_error = f"{field}: {str(exc)[:120]}"
                    logger.debug(f"Firing-stats field '{field}' errored: {last_error}")
                    continue
                finally:
                    pass

            try:
                await client.close()
            except Exception:
                pass

            if winner is None:
                # No field worked, or all returned empty. Treat as
                # "unavailable" so the UI doesn't render a useless "0 hits"
                # column for every rule when really we just can't tell.
                self._unavailable_reason = last_error or "No rule-ID field returned hits in the alerts index."
                self._last_refresh = datetime.utcnow()
                logger.warning(
                    f"Could not resolve a rule-ID field for firing stats. {self._unavailable_reason}",
                )
                return len(self._stats)

            self._stats = new_stats
            self._winning_field = winner
            self._unavailable_reason = None
            self._last_refresh = datetime.utcnow()
            logger.info(
                f"Loaded firing stats for {len(self._stats)} rule(s) using field '{winner}'",
            )
            return len(self._stats)

    # ---- accessors --------------------------------------------------------

    def get(self, rule_id: int) -> Dict[str, Any]:
        """
        Return ``{"hits_30d": int, "hits_7d": int, "last_seen": str | None}``
        for ``rule_id``.

        Missing rule IDs return zero counts + None last_seen — the rule
        exists in the cache but simply hasn't fired in the 30d window.
        Callers that need to distinguish "0 hits" from "stats unavailable"
        should check ``is_available`` separately.
        """
        return self._stats.get(
            rule_id,
            {"hits_30d": 0, "hits_7d": 0, "last_seen": None},
        )


# ---------------------------------------------------------------------------
# Per-customer firing stats — on-demand, not cached
# ---------------------------------------------------------------------------


async def fetch_firing_stats_for_customer(customer_code: str) -> Dict[int, Dict[str, Any]]:
    """
    Run the firing-stats aggregation filtered to a single customer code.

    Why this isn't cached:
    The catalog has potentially dozens of customer codes; pre-caching all of
    them would balloon memory and waste indexer cycles on customers nobody
    is looking at. Instead we run the query on demand when an analyst picks
    a customer from the dropdown. The query is the same shape as the global
    refresh (one terms agg + sub-aggs), just with an extra term filter on
    ``agent_labels_customer`` — sub-second on any realistic deployment.

    Returns ``{rule_id: {hits_30d, hits_7d, last_seen}}`` — same shape as
    ``WazuhRulesFiringStatsCache.get()`` so callers can use it
    interchangeably. Empty dict when:
    - The customer code doesn't match any alerts in the 30d window.
    - The winning_field couldn't be determined (indexer error / no field).
    - The indexer is unreachable.

    All failures are silent / non-raising — the catalog falls back to "0
    hits for this customer" rather than erroring.

    Field naming note: the customer code is conventionally indexed under
    ``agent_labels_customer`` (Graylog convention, flat) in SOCFortress
    deployments — confirmed in the Suricata alert sample we tested. Wazuh
    vanilla uses ``agent.labels.customer`` (nested). We try both.
    """
    from app.connectors.wazuh_indexer.utils.universal import (
        create_wazuh_indexer_client_async,
    )

    if not customer_code or not customer_code.strip():
        return {}

    # Use whatever rule-ID field the global cache discovered — saves us from
    # re-running the field-fallback dance per customer query.
    field = wazuh_firing_stats_cache._winning_field or RULE_ID_FIELD_OPTIONS[0]

    try:
        client = await create_wazuh_indexer_client_async()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Per-customer firing stats: indexer unavailable ({_short_reason(exc)})")
        return {}

    try:
        # Try each customer-code field shape until one returns buckets.
        # Same fallback philosophy as the rule-ID field discovery.
        for customer_field in ("agent_labels_customer", "agent.labels.customer"):
            try:
                body = _build_firing_stats_query(field)
                # Splice the customer filter into the existing query — keeps
                # the agg shape identical so the bucket-unpacking code below
                # matches the cached path exactly.
                body["query"]["bool"]["filter"].append(
                    {"term": {customer_field: customer_code}},
                )
                response = await client.search(
                    index=ALERT_INDEX_PATTERN,
                    body=body,
                    ignore_unavailable=True,
                    allow_no_indices=True,
                )
                buckets = response.get("aggregations", {}).get("by_rule", {}).get("buckets", [])
                if not buckets:
                    continue

                out: Dict[int, Dict[str, Any]] = {}
                for bucket in buckets:
                    rule_id = _coerce_rule_id(bucket.get("key"))
                    if rule_id is None:
                        continue
                    out[rule_id] = {
                        "hits_30d": int(bucket.get("doc_count") or 0),
                        "hits_7d": int(bucket.get("last_7d", {}).get("doc_count") or 0),
                        "last_seen": (bucket.get("last_seen") or {}).get("value_as_string"),
                    }
                logger.debug(
                    f"Per-customer firing stats: {len(out)} rules for customer " f"{customer_code!r} via field {customer_field!r}",
                )
                return out
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    f"Per-customer firing stats: customer field {customer_field!r} failed: {exc}",
                )
                continue
        return {}
    finally:
        try:
            await client.close()
        except Exception:
            pass


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


async def _discover_alert_indices(client: Any) -> List[str]:
    """
    List every index in the cluster and return the ones that look like
    alert indices (i.e. not a system / Wazuh-internal / audit-log index).

    Returns a list of concrete index names — pass directly to
    ``client.search(index=<list>)``. Returns ``[]`` on any failure or if
    the cluster is empty; callers should fall back to a sensible default
    pattern in that case.

    Why this is safe even with vendor indices that aren't Wazuh-alert
    shaped:

    - The aggregation's ``exists`` filter on the rule-ID field drops
      documents that don't carry one.
    - ``_coerce_rule_id`` drops bucket keys that aren't integer-parseable —
      vendor-native rule identifiers like ``"Office365_FailedLogin"``
      don't pollute the Wazuh rule cache.

    So the worst case of including a "wrong" index is zero contribution,
    not garbage data. Erring on the side of inclusion is correct.
    """
    try:
        # ``cat.indices`` returns a list of dicts with at least an ``index``
        # field when ``format="json"``. We only need the name; ``h="index"``
        # restricts the columns to keep the response small.
        cat_response = await client.cat.indices(format="json", h="index")
    except Exception as exc:  # noqa: BLE001
        # Permission errors, network blips, etc. Caller falls back.
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
