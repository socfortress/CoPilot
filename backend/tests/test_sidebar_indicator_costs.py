"""The two most expensive sidebar indicators, pinned (#1072).

Per-indicator timings from a real session showed where the sidebar's remaining
seconds went:

* `build_influx_health_indicator` — 4.1s, a Flux query over a day of the
  _monitoring bucket, run on every single sidebar load.
* `build_scheduler_indicator_excluding_agent_sync` — 1.7s, which turned out to
  be an N+1: one SELECT per scheduled job.

Both fixes are invisible in normal use and easy to undo by accident, so the
properties are asserted rather than trusted.

Run with: cd backend && python -m pytest tests/test_sidebar_indicator_costs.py
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.status.services import context_indicators as indicators  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_influx_cache():
    indicators._influx_indicator_cache = None
    indicators._influx_indicator_cached_at = None
    yield
    indicators._influx_indicator_cache = None
    indicators._influx_indicator_cached_at = None


def _session():
    return MagicMock(spec=AsyncSession)


# ── the InfluxDB indicator: refreshed off the request path ─────────────────


def test_sidebar_never_runs_the_influx_query_itself(monkeypatch):
    """The sidebar reads the last known value; it must not query InfluxDB.

    This was the whole sidebar once everything else was parallelised: a 4-5s Flux
    query on every load. A TTL cache alone did not fix it, because /status/sidebar
    is fetched about once per app load and so never hits its own cache.
    """
    calls = 0

    async def fake_build(session):
        nonlocal calls
        calls += 1
        return SimpleNamespace(id="influx_health")

    monkeypatch.setattr(indicators, "_build_influx_health_indicator", fake_build)
    monkeypatch.setattr(indicators, "_schedule_influx_refresh", lambda: None)

    indicator = asyncio.run(indicators.build_influx_health_indicator(_session()))

    assert calls == 0, "the sidebar must not run the Flux query on the request path"
    # Honest placeholder rather than a wrong "all clear" or an empty count.
    assert "Checking" in indicator.detail


def test_sidebar_serves_the_refreshed_value(monkeypatch):
    """Once the scheduled job has run, the sidebar returns its result."""
    built = SimpleNamespace(id="influx_health", detail="No active critical InfluxDB alerts.")

    async def fake_build(session):
        return built

    monkeypatch.setattr(indicators, "_build_influx_health_indicator", fake_build)

    @asynccontextmanager
    async def fake_session():
        yield _session()

    monkeypatch.setattr(indicators, "get_db_session", fake_session)

    async def scenario():
        await indicators.refresh_influx_health_indicator()
        return await indicators.build_influx_health_indicator(_session())

    assert asyncio.run(scenario()) is built


def test_a_cold_sidebar_load_schedules_a_refresh(monkeypatch):
    """Nobody waits, but the value must arrive for the next caller."""
    scheduled = []
    monkeypatch.setattr(indicators, "_schedule_influx_refresh", lambda: scheduled.append(True))

    asyncio.run(indicators.build_influx_health_indicator(_session()))

    assert scheduled == [True]


def test_concurrent_refreshes_run_the_query_once(monkeypatch):
    """The scheduled job and a startup warm-up must not both pay for it."""
    calls = 0

    async def slow_build(session):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return SimpleNamespace(id="influx_health")

    monkeypatch.setattr(indicators, "_build_influx_health_indicator", slow_build)

    @asynccontextmanager
    async def fake_session():
        yield _session()

    monkeypatch.setattr(indicators, "get_db_session", fake_session)

    async def scenario():
        await asyncio.gather(*[indicators.refresh_influx_health_indicator() for _ in range(4)])

    asyncio.run(scenario())

    assert calls == 1, f"four concurrent refreshes ran the query {calls} times"


def test_expired_value_is_replaced_not_served(monkeypatch):
    stale = SimpleNamespace(id="influx_health", detail="stale")
    indicators._influx_indicator_cache = stale
    indicators._influx_indicator_cached_at = datetime.utcnow() - timedelta(
        seconds=indicators._INFLUX_INDICATOR_TTL_SECONDS + 1,
    )
    monkeypatch.setattr(indicators, "_schedule_influx_refresh", lambda: None)

    indicator = asyncio.run(indicators.build_influx_health_indicator(_session()))

    assert indicator is not stale, "an expired value must not be served"


# ── the scheduler indicator: one query, not one per job ─────────────────────


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows, first=lambda: self._rows[0] if self._rows else None)


def test_scheduler_indicator_issues_a_single_query(monkeypatch):
    """The N+1 that made this the second-most expensive indicator."""
    executed = []

    jobs = [SimpleNamespace(id=f"job_{n}") for n in range(12)]
    monkeypatch.setattr(
        indicators,
        "get_scheduler_instance",
        lambda: asyncio.sleep(0, result=SimpleNamespace(get_jobs=lambda: jobs)),
    )

    rows = [SimpleNamespace(job_id=job.id, enabled=True, time_interval=5, last_success=datetime.utcnow()) for job in jobs]

    session = MagicMock(spec=AsyncSession)

    async def execute(statement):
        executed.append(statement)
        return _FakeResult(rows)

    session.execute = execute

    indicator = asyncio.run(indicators.build_scheduler_indicator_excluding_agent_sync(session))

    assert len(executed) == 1, f"expected one query for all {len(jobs)} jobs, got {len(executed)}"
    assert indicator.status == "ok"


def test_scheduler_indicator_still_flags_stale_jobs(monkeypatch):
    """The optimisation must not change what the indicator reports."""
    jobs = [SimpleNamespace(id="fresh_job"), SimpleNamespace(id="stale_job")]
    monkeypatch.setattr(
        indicators,
        "get_scheduler_instance",
        lambda: asyncio.sleep(0, result=SimpleNamespace(get_jobs=lambda: jobs)),
    )

    now = datetime.utcnow()
    rows = [
        SimpleNamespace(job_id="fresh_job", enabled=True, time_interval=5, last_success=now),
        SimpleNamespace(job_id="stale_job", enabled=True, time_interval=5, last_success=now - timedelta(hours=4)),
    ]

    session = MagicMock(spec=AsyncSession)

    async def execute(statement):
        return _FakeResult(rows)

    session.execute = execute

    indicator = asyncio.run(indicators.build_scheduler_indicator_excluding_agent_sync(session))

    assert indicator.count == 1
    assert "stale_job" in indicator.detail


def test_scheduler_indicator_makes_no_query_when_there_are_no_jobs(monkeypatch):
    """`.in_([])` is a pointless round-trip, and on some backends a warning."""
    monkeypatch.setattr(
        indicators,
        "get_scheduler_instance",
        lambda: asyncio.sleep(0, result=SimpleNamespace(get_jobs=lambda: [])),
    )

    executed = []
    session = MagicMock(spec=AsyncSession)

    async def execute(statement):
        executed.append(statement)
        return _FakeResult([])

    session.execute = execute

    indicator = asyncio.run(indicators.build_scheduler_indicator_excluding_agent_sync(session))

    assert executed == []
    assert indicator.status == "ok"
