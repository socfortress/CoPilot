"""`/graylog/metrics` fetches its two sources concurrently (#1072).

The endpoint reads two independent Graylog endpoints — `/api/system/metrics` and
`/api/system/journal` — and neither uses the other's result. Awaited one after
the other, the request cost the sum of both round-trips: a steady ~3.1s in every
measured session, which also makes it the cost of every sidebar healthcheck poll.

Gathering them is only worth anything now that the Graylog connector no longer
blocks the event loop (level 0): before, the second call could not have started
while the first was in flight regardless of how it was written.

Run with: cd backend && python -m pytest tests/test_graylog_metrics_concurrency.py
"""

import asyncio
import os
import time

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.graylog.services import monitoring  # noqa: E402

ROUND_TRIP = 0.2

METRICS_PAYLOAD = {
    "success": True,
    "data": {"gauges": {}, "counters": {}},
}
JOURNAL_PAYLOAD = {
    "success": True,
    "data": {"uncommitted_journal_entries": 7},
}


def _slow(payload, started):
    async def fetch():
        started.append(time.perf_counter())
        await asyncio.sleep(ROUND_TRIP)
        return payload

    return fetch


def test_the_two_graylog_calls_overlap(monkeypatch):
    started = []
    monkeypatch.setattr(monitoring, "fetch_metrics_from_graylog", _slow(METRICS_PAYLOAD, started))
    monkeypatch.setattr(monitoring, "fetch_uncommitted_journal_entries", _slow(JOURNAL_PAYLOAD, started))

    begun = time.perf_counter()
    response = asyncio.run(monitoring.get_metrics())
    elapsed = time.perf_counter() - begun

    assert response.success
    assert len(started) == 2
    # Sequentially this is 2 * ROUND_TRIP; concurrently it is bounded by one.
    assert elapsed < ROUND_TRIP * 1.6, f"the two calls did not overlap: {elapsed:.2f}s"
    assert abs(started[1] - started[0]) < ROUND_TRIP / 2, "the second call waited for the first"


def test_the_response_still_carries_both_sources(monkeypatch):
    """Gathering must not reorder or drop either payload."""
    monkeypatch.setattr(monitoring, "fetch_metrics_from_graylog", _slow(METRICS_PAYLOAD, []))
    monkeypatch.setattr(monitoring, "fetch_uncommitted_journal_entries", _slow(JOURNAL_PAYLOAD, []))

    response = asyncio.run(monitoring.get_metrics())

    # The journal count comes from the *second* call; a swapped gather order would
    # silently read it from the wrong payload.
    assert response.uncommitted_journal_entries == 7
    assert response.success


def test_a_failing_source_does_not_produce_a_bogus_success(monkeypatch):
    """One Graylog endpoint failing must not be reported as healthy."""
    monkeypatch.setattr(monitoring, "fetch_metrics_from_graylog", _slow(METRICS_PAYLOAD, []))
    monkeypatch.setattr(
        monitoring,
        "fetch_uncommitted_journal_entries",
        _slow({"success": False, "data": {}}, []),
    )

    response = asyncio.run(monitoring.get_metrics())

    assert not response.success
    assert response.uncommitted_journal_entries == 0
