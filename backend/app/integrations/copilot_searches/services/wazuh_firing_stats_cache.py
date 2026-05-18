"""
In-memory cache of per-rule firing counts from the Wazuh indexer.

Why this exists:
The catalog wants to surface "how often has this rule fired in the last
7d/30d?" for every Wazuh rule. The naive way (one ES query per rule, per
request, per user) would crush the indexer. Instead we do **one** terms
aggregation over the alerts index, cache the result, and serve every
per-rule lookup from the dict.

Cost: one search request to the Wazuh indexer every ``CACHE_TTL_MINUTES``
minutes (15 by default). The aggregation is a date-filtered ``terms`` over
rule.id with a sub-aggregation for the 7d sub-window. Even on indices with
hundreds of millions of docs, this returns in well under a second
(Elasticsearch is built for exactly this shape of query).

Field-name fallback:
Wazuh's indexer schema varies across versions and shipping configurations.
The rule ID may live under ``rule.id`` (object mapping), ``rule_id`` (flat
mapping), or just ``id`` (older schemas). We try them in that order, taking
the first one that returns non-empty buckets — same fallback pattern used
in ``app/connectors/wazuh_manager/services/mitre.py``.

No DB writes, no schema changes, no Alembic migrations — pure read-only
aggregation against the alerts index plus an in-memory dict on the CoPilot
side.
"""

import asyncio
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
INDEX_PATTERN = "wazuh-*"

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
                    response = await client.search(index=INDEX_PATTERN, body=body)
                    buckets = (
                        response.get("aggregations", {})
                        .get("by_rule", {})
                        .get("buckets", [])
                    )
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
                        new_stats[rule_id] = {
                            "hits_30d": hits_30d,
                            "hits_7d": hits_7d,
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
                self._unavailable_reason = (
                    last_error or "No rule-ID field returned hits in the alerts index."
                )
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

    def get(self, rule_id: int) -> Dict[str, int]:
        """
        Return ``{"hits_30d": int, "hits_7d": int}`` for ``rule_id``.

        Missing rule IDs return zeros — the rule exists in the cache but
        simply hasn't fired in the 30d window. Callers that need to
        distinguish "0 hits" from "stats unavailable" should check
        ``is_available`` separately.
        """
        return self._stats.get(rule_id, {"hits_30d": 0, "hits_7d": 0})


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
                },
            },
        },
    }


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
