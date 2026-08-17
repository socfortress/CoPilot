"""The sidebar fans out its indicators without sharing a session (#1072).

`build_sidebar_context` used to await up to 14 indicator builders in a `for`
loop, so `GET /api/status/sidebar` cost the *sum* of all of them — one request
was recorded in flight for 15 seconds.

Fanning them out has two hard constraints, and both are asserted here because
getting either wrong fails in the worst way: intermittently, under load.

* **One AsyncSession cannot serve concurrent operations.** Every builder
  therefore gets a private session; none may touch the caller's.
* **The connection pool is finite.** A single sidebar request must not be able
  to drain it while other requests are being served, so concurrency is bounded.

Run with: cd backend && python -m pytest tests/test_sidebar_context_concurrency.py
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.status.services import context as context_module  # noqa: E402

SLOW = 0.2
FAST = 0.02


def _session():
    """An object that passes `isinstance(x, AsyncSession)` without a database."""
    return MagicMock(spec=AsyncSession)


def _indicator(name):
    return MagicMock(id=name)


@pytest.fixture()
def sessions(monkeypatch):
    """Hand out a distinct session per `get_db_session()` call, and record them."""
    handed_out = []

    @asynccontextmanager
    async def fake_get_db_session():
        session = _session()
        handed_out.append(session)
        yield session

    monkeypatch.setattr(context_module, "get_db_session", fake_get_db_session)
    return handed_out


def test_all_indicators_run_concurrently_and_order_is_preserved(sessions):
    caller_session = _session()
    in_flight = 0
    peak = 0

    async def builder(session, tag):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(SLOW)
        in_flight -= 1
        return _indicator(tag)

    def make(tag):
        async def run(session):
            return await builder(session, tag)

        run.__name__ = f"build_{tag}"
        return run

    tags = ["a", "b", "c", "d", "e"]
    builders = [(make(tag), (caller_session,), {}) for tag in tags]

    started = time.perf_counter()
    indicators = asyncio.run(context_module._gather_indicators(builders))
    elapsed = time.perf_counter() - started

    # The sidebar renders indicators in declaration order, so gather must not
    # reorder them into completion order.
    assert [i.id for i in indicators] == tags

    # Serially this is 5 * 200ms; concurrently it is bounded by the slowest.
    assert elapsed < SLOW * 2, f"builders did not overlap: {elapsed:.2f}s"
    assert peak >= 5, f"expected all five to overlap, peak was {peak}"


def test_no_builder_uses_the_caller_session(sessions):
    """Concurrent use of one AsyncSession is the bug this design avoids."""
    caller_session = _session()
    seen = []

    async def builder(session):
        seen.append(session)
        await asyncio.sleep(FAST)
        return _indicator("x")

    builders = [(builder, (caller_session,), {}) for _ in range(4)]
    asyncio.run(context_module._gather_indicators(builders))

    assert caller_session not in seen, "a concurrent builder must never use the caller's session"
    assert len(set(id(s) for s in seen)) == 4, "each concurrent builder needs its own session"


def test_concurrency_is_bounded_so_one_request_cannot_drain_the_pool(monkeypatch, sessions):
    """Without a bound, simultaneous sidebars would starve every other request."""
    monkeypatch.setattr(context_module, "INDICATOR_CONCURRENCY", 3)

    caller_session = _session()
    in_flight = 0
    peak = 0

    async def builder(session):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(FAST)
        in_flight -= 1
        return _indicator("x")

    builders = [(builder, (caller_session,), {}) for _ in range(12)]
    indicators = asyncio.run(context_module._gather_indicators(builders))

    assert len(indicators) == 12
    assert peak <= 3, f"concurrency bound ignored: {peak} builders held a connection at once"
    assert peak > 1, "the bound must not serialise everything"


def test_builders_without_a_session_argument_are_left_alone(sessions):
    """Not every indicator needs the database."""
    captured = []

    async def no_session_builder():
        captured.append("ran")
        return _indicator("standalone")

    indicators = asyncio.run(context_module._gather_indicators([(no_session_builder, (), {})]))

    assert captured == ["ran"]
    assert [i.id for i in indicators] == ["standalone"]
    assert not sessions, "a builder that takes no session must not check one out of the pool"


def test_a_failing_builder_is_skipped_not_fatal(sessions):
    """One unreachable service must not blank the whole sidebar."""
    caller_session = _session()

    async def exploding(session):
        raise RuntimeError("service unreachable")

    async def healthy(session):
        return _indicator("healthy")

    builders = [(exploding, (caller_session,), {}), (healthy, (caller_session,), {})]
    indicators = asyncio.run(context_module._gather_indicators(builders))

    assert [i.id for i in indicators] == ["healthy"]
