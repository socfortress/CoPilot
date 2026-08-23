"""Process-wide cache for connector credentials (#1072, level 4).

Level 2 established the number that reframes this whole effort: **every
statement on this deployment costs ~135ms regardless of what it does** (p50
134.2–134.8ms across four sessions and 3,317 queries). The lever is the *number*
of round-trips per request, not the SQL inside them.

With the per-request user lookup fixed (level 3), the largest remaining consumer
is the connector credential read: 244 queries in one session, **3.4 per
request**, and rising as more integrations land. `get_connector_info_from_db` is
called from 89 sites across 22 modules — every outbound call to Wazuh, Graylog,
Velociraptor, Cortex, InfluxDB, Shuffle, Talon… first asks the database where to
go and with what key.

The cost is worse than the call count suggests. `Connectors.history_logs` is
declared `lazy="selectin"`, so each of those reads fires a *second* statement
against `connectorhistory` — and nothing in the codebase reads `history_logs`
off this path. Caching removes both.

There are **two** funnels into this table, and caching only one leaves roughly a
quarter of the reads in place. `app/utils.py:get_connector_attribute` has a
further 88 call sites and reads the same row for a single column, addressed
either by name or — in a handful of places — by id. Both now read through here;
the id map below is what lets the id form share the same entries.

**Why this is safe to cache when most things are not:** connector configuration
is deployment-wide (one row per tool, no tenant dimension — see CLAUDE.md,
"Connector credentials are global") and changes only when an operator changes it.
Every write path is in `ConnectorServices` and invalidates this cache
immediately after its commit. The TTL is a backstop for the one case
invalidation cannot see — someone editing the table directly — not the primary
correctness mechanism.

Two deliberate non-features:

* **Misses are not cached.** A `None` means the connector row does not exist yet;
  remembering that would make a newly-added connector invisible for the whole
  TTL. The same reasoning applies to the user cache in `app/auth/utils.py`.
* **Nothing is pre-warmed.** The first caller of each connector pays one lookup.
  Pre-warming would put 20+ queries into startup to save them from a request
  that may never come.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from typing import Dict
from typing import Optional

from loguru import logger


def _ttl_seconds() -> int:
    """Read at import; `0` disables the cache, which is how you A/B it."""
    raw = os.getenv("CONNECTOR_CACHE_TTL_SECONDS", "600")
    try:
        return max(int(raw), 0)
    except ValueError:
        logger.warning(f"CONNECTOR_CACHE_TTL_SECONDS={raw!r} is not an integer; falling back to 600s")
        return 600


TTL_SECONDS = _ttl_seconds()

# `time.monotonic`, not `datetime.utcnow`: an NTP step backwards would otherwise
# leave an entry that never expires, and credentials are the wrong thing to be
# wrong about indefinitely.
_entries: Dict[str, tuple[float, Dict[str, Any]]] = {}
_locks: Dict[str, asyncio.Lock] = {}

# `connector_id` → `connector_name`, for the minority of call sites that address
# a connector by id (`get_connector_attribute(connector_id=10, …)`). Kept
# separately from `_entries` and *not* subject to the TTL: a row's id and name
# are its identity and only change when the row is recreated, which happens in
# the startup sync — and that calls `invalidate_all()`.
_names_by_id: Dict[int, str] = {}

_hits = 0
_misses = 0
_invalidations = 0


def _copy(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Hand out a copy, never the stored dict.

    Callers today only read (`attributes["connector_url"]` and friends), but a
    future one that mutates its result would otherwise silently corrupt every
    subsequent caller's credentials. A shallow copy of ~19 scalars costs
    microseconds against a 135ms round-trip; `history_logs` is a list nobody
    reads, so it is copied by reference on purpose.
    """
    return dict(payload)


def _peek(connector_name: str) -> Optional[Dict[str, Any]]:
    """A pure lookup: no counters, no locking. Not the entry point."""
    if TTL_SECONDS == 0:
        return None

    entry = _entries.get(connector_name)
    if entry is None:
        return None

    stored_at, payload = entry
    if time.monotonic() - stored_at >= TTL_SECONDS:
        # Expired: drop it rather than leave it for the next caller to re-check.
        _entries.pop(connector_name, None)
        return None

    return _copy(payload)


def lock_for(connector_name: str) -> asyncio.Lock:
    """Serialise cold lookups of one connector.

    Without this the fan-outs built earlier in #1072 stampede: `/status/sidebar`
    runs 14 indicator builders concurrently and several ask for the same
    connector, so a cold cache turns into 14 identical queries instead of one.
    Per name, so a slow Velociraptor lookup never blocks a Graylog one.
    """
    lock = _locks.get(connector_name)
    if lock is None:
        lock = asyncio.Lock()
        _locks[connector_name] = lock
    return lock


async def get_or_load(connector_name: str, loader) -> Optional[Dict[str, Any]]:
    """Read through the cache, loading at most once per connector.

    The read-through lives here rather than at the call site so that one place
    owns all three invariants — the double-check under the lock, the decision
    not to cache a miss, and the hit/miss accounting. Doing it by hand at the
    call site got the last one wrong immediately: the recheck inside the lock
    counted a *second* miss for the same request, understating the hit ratio
    that is the whole point of measuring this.

    Args:
        connector_name: the cache key, and the name the loader will look up.
        loader: an async callable returning the payload dict, or None if the
            connector does not exist.
    """
    global _hits, _misses

    cached = _peek(connector_name)
    if cached is not None:
        _hits += 1
        return cached

    async with lock_for(connector_name):
        # Someone may have loaded it while we waited. Still a hit for this
        # caller — it never reached the database.
        cached = _peek(connector_name)
        if cached is not None:
            _hits += 1
            return cached

        _misses += 1
        payload = await loader()
        if payload is None:
            # Deliberately not cached — a missing row usually means "not created
            # yet", and remembering it would hide the connector for a whole TTL.
            return None

        if TTL_SECONDS > 0:
            _entries[connector_name] = (time.monotonic(), _copy(payload))
        remember_id(payload.get("id"), connector_name)
        return _copy(payload)


def remember_id(connector_id: Optional[int], connector_name: str) -> None:
    """Record the id → name mapping seen on a load."""
    if connector_id is not None:
        _names_by_id[connector_id] = connector_name


def name_for_id(connector_id: int) -> Optional[str]:
    """The connector's name, if this process has ever loaded that row."""
    return _names_by_id.get(connector_id)


def invalidate(connector_name: Optional[str]) -> None:
    """Forget one connector. Called after every committed write to its row."""
    global _invalidations

    if not connector_name:
        return
    if _entries.pop(connector_name, None) is not None:
        _invalidations += 1
        logger.debug(f"Connector cache invalidated for {connector_name}")


def invalidate_all() -> None:
    """Forget everything — used by the startup sync and by the tests.

    The id map goes too: the startup sync is the one place that deletes and
    recreates connector rows, so it is also the one place an id could come back
    attached to a different name.
    """
    global _invalidations

    _invalidations += len(_entries)
    _entries.clear()
    _names_by_id.clear()


def reset_stats() -> None:
    """Test seam. Production never needs this; the counters are cumulative."""
    global _hits, _misses, _invalidations

    _hits = _misses = _invalidations = 0


def stats() -> Dict[str, Any]:
    """Surfaced in the performance session log, so the next session measures it."""
    looked_up = _hits + _misses
    return {
        "entries": len(_entries),
        "hits": _hits,
        "misses": _misses,
        "invalidations": _invalidations,
        "hit_ratio": round(_hits / looked_up, 4) if looked_up else None,
        "ttl_seconds": TTL_SECONDS,
    }
