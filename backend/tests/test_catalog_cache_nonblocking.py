"""No catalog request may wait for a cold cache (#1072).

The Detections Catalog reads from four in-memory caches that used to load lazily
inside whichever request found them stale. Measured consequences, from a real
session: `/catalog/stories` at 167s and `/catalog/stats` at 139s — and requests
arriving during a load queued on the same lock, so the second pair waited for the
first pair to finish waiting.

Now every cache refreshes in the background: a request serves the snapshot it has
and reports `loading` so the UI can distinguish "not loaded yet" from "nothing
found". These tests pin that a request cannot be made to wait, and that a burst
of them starts one download rather than one each.

Run with: cd backend && python -m pytest tests/test_catalog_cache_nonblocking.py
"""

import asyncio
import os
import time

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations.copilot_searches.services.cache_support import (  # noqa: E402
    BackgroundRefreshMixin,
)

SLOW_LOAD = 0.3


class _Cache(BackgroundRefreshMixin):
    """Stand-in for a catalog cache with a slow refresh."""

    def __init__(self, stale=True, duration=SLOW_LOAD):
        self._stale = stale
        self._duration = duration
        self.refresh_calls = 0

    @property
    def is_stale(self):
        return self._stale

    async def refresh(self):
        self.refresh_calls += 1
        await asyncio.sleep(self._duration)
        self._stale = False


def test_a_request_never_waits_for_a_cold_cache():
    """The 167s failure mode: a user request awaiting a full download."""

    async def scenario():
        cache = _Cache()
        started = time.perf_counter()
        await cache.ensure_fresh_nonblocking()
        elapsed = time.perf_counter() - started

        assert cache.is_loading, "a stale cache should have started refreshing"

        # Let the background refresh finish so the task does not outlive the test.
        await asyncio.sleep(SLOW_LOAD * 2)
        return elapsed, cache

    elapsed, cache = asyncio.run(scenario())

    assert elapsed < SLOW_LOAD / 3, f"the caller waited {elapsed * 1000:.0f}ms for a background load"
    assert cache.refresh_calls == 1, "the refresh must still have happened"
    assert not cache.is_loading


def test_a_burst_of_requests_starts_one_refresh():
    """Concurrent requests on a cold cache must not each start a download."""

    async def scenario():
        cache = _Cache()
        await asyncio.gather(*[cache.ensure_fresh_nonblocking() for _ in range(10)])
        await asyncio.sleep(SLOW_LOAD * 2)
        return cache

    cache = asyncio.run(scenario())

    assert cache.refresh_calls == 1, f"{cache.refresh_calls} downloads were started instead of one"


def test_a_fresh_cache_starts_nothing():
    async def scenario():
        cache = _Cache(stale=False)
        await cache.ensure_fresh_nonblocking()
        return cache

    cache = asyncio.run(scenario())

    assert cache.refresh_calls == 0
    assert not cache.is_loading


def test_a_failing_refresh_does_not_escape_and_clears_the_flag():
    """A GitHub outage must degrade the catalog, not fail requests."""

    class Exploding(_Cache):
        async def refresh(self):
            self.refresh_calls += 1
            raise RuntimeError("github unreachable")

    async def scenario():
        cache = Exploding()
        await cache.ensure_fresh_nonblocking()
        await asyncio.sleep(0.05)
        return cache

    cache = asyncio.run(scenario())

    assert cache.refresh_calls == 1
    # The flag must clear, or `schedule_background_refresh` would refuse to ever
    # retry and the cache would stay empty for the process's lifetime.
    assert not cache.is_loading, "a failed refresh must not leave the cache stuck loading"


def test_a_later_request_can_retry_after_a_failure():
    class ExplodingOnce(_Cache):
        async def refresh(self):
            self.refresh_calls += 1
            if self.refresh_calls == 1:
                raise RuntimeError("transient")
            self._stale = False

    async def scenario():
        cache = ExplodingOnce()
        await cache.ensure_fresh_nonblocking()
        await asyncio.sleep(0.05)
        await cache.ensure_fresh_nonblocking()
        await asyncio.sleep(0.05)
        return cache

    cache = asyncio.run(scenario())

    assert cache.refresh_calls == 2, "a transient failure must not disable refreshing"
    assert not cache.is_stale


def test_the_real_catalog_caches_use_the_mixin():
    """A cache that forgets to inherit it silently reintroduces the blocking load."""
    from app.integrations.copilot_searches.services.copilot_searches import rules_cache
    from app.integrations.copilot_searches.services.mitre_coverage import mitre_matrix
    from app.integrations.copilot_searches.services.wazuh_firing_stats_cache import (
        wazuh_firing_stats_cache,
    )
    from app.integrations.copilot_searches.services.wazuh_rules_cache import (
        wazuh_rules_cache,
    )

    for cache in (rules_cache, mitre_matrix, wazuh_firing_stats_cache, wazuh_rules_cache):
        assert isinstance(cache, BackgroundRefreshMixin), f"{type(cache).__name__} lost its background refresh"


def test_catalog_reports_loading_while_a_cache_is_cold(monkeypatch):
    """An empty snapshot must not read as "this deployment has no detections"."""
    from app.integrations.copilot_searches.services import detection_catalog

    assert detection_catalog.catalog_is_loading() is False

    monkeypatch.setattr(
        type(detection_catalog.rules_cache),
        "is_loading",
        property(lambda self: True),
    )
    assert detection_catalog.catalog_is_loading() is True
