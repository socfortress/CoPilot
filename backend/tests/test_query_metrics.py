"""Measure the database instead of inferring it (#1072, level 2).

Every earlier statement about the database was an inference: `/api/customers`
takes 1.6s and issues three queries, therefore a query costs ~500ms. That guess
cannot distinguish three problems with three different fixes — a slow query, a
request queueing for a connection, or a fixed per-round-trip cost that every
statement pays. This instrumentation measures all three.

The tests run against a real SQLAlchemy engine (in-memory SQLite) rather than
mocks: the whole value is that the listeners fire on actual cursor execution, and
a mock would assert nothing about that.

Run with: cd backend && python -m pytest tests/test_query_metrics.py
"""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.db import query_metrics  # noqa: E402
from app.db.query_metrics import digest  # noqa: E402


@pytest.fixture()
def engine():
    """A real async engine, with the listeners installed on it."""
    query_metrics.query_registry.reset()
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    query_metrics.install(eng)
    yield eng
    asyncio.run(eng.dispose())
    query_metrics.query_registry.reset()


def _run(engine, statements):
    async def scenario():
        async with engine.connect() as conn:
            for sql, params in statements:
                await conn.execute(text(sql), params or {})

    asyncio.run(scenario())


def test_real_queries_are_timed(engine):
    """The listeners must fire on actual cursor execution, not on a wrapper."""
    _run(engine, [("SELECT 1", None), ("SELECT 2", None)])

    registry = query_metrics.query_registry
    assert registry.total_queries >= 2
    assert registry.total_ms > 0
    assert all(d >= 0 for d in registry.durations)


def test_the_same_query_shape_groups_into_one_row(engine):
    """Otherwise the table is one row per execution and tells you nothing."""
    _run(engine, [("SELECT :v", {"v": n}) for n in range(5)])

    rows = [s for s in query_metrics.query_registry.statements if "SELECT" in s.statement]
    assert len(rows) == 1, f"expected one grouped row, got {[r.statement for r in rows]}"
    assert rows[0].count == 5


def test_in_lists_of_different_lengths_group_together():
    """`WHERE id IN (%s, %s)` must not open a new row per parameter count."""
    two = digest("SELECT * FROM t WHERE id IN (%s, %s)")
    five = digest("SELECT * FROM t WHERE id IN (%s, %s, %s, %s, %s)")

    assert two == five
    assert "IN (...)" in two


def test_no_literal_values_are_recorded(engine):
    """The log must never carry user data — statements stay parameterised."""
    _run(engine, [("SELECT :secret", {"secret": "hunter2-should-never-appear"})])

    blob = " ".join(s.statement for s in query_metrics.query_registry.statements)
    assert "hunter2" not in blob


def test_a_slow_query_is_reported_to_the_session_log(monkeypatch):
    """Slow statements land in the same file as the requests they explain."""
    recorded = []
    from app.middleware import performance

    monkeypatch.setattr(
        performance.performance_registry,
        "record_event",
        lambda kind, payload: recorded.append((kind, payload)),
    )

    query_metrics.query_registry.reset()
    query_metrics.query_registry.record("SELECT slow", query_metrics.SLOW_QUERY_MS + 10)

    assert recorded and recorded[0][0] == "slow_query"
    assert recorded[0][1]["statement"] == "SELECT slow"
    assert query_metrics.query_registry.slow_queries == 1


def test_a_fast_query_is_not_reported(monkeypatch):
    recorded = []
    from app.middleware import performance

    monkeypatch.setattr(
        performance.performance_registry,
        "record_event",
        lambda kind, payload: recorded.append(kind),
    )

    query_metrics.query_registry.reset()
    query_metrics.query_registry.record("SELECT fast", 1.0)

    assert recorded == []


def test_the_statement_table_is_bounded(monkeypatch):
    """A query shape per row is fine; unbounded growth is not."""
    monkeypatch.setattr(query_metrics, "MAX_STATEMENTS", 5)
    query_metrics.query_registry.reset()

    for n in range(50):
        query_metrics.query_registry.record(f"SELECT col{n} FROM t", 1.0)

    assert len(query_metrics.query_registry.statements) <= 5
    assert query_metrics.query_registry.dropped_statements > 0
    # Dropped rows must still be counted, or the totals silently understate.
    assert query_metrics.query_registry.total_queries == 50


# ── the verdict: the whole point of level 2 ─────────────────────────────────


def _summary_with(durations, pool_exhausted=0, pool_samples=0):
    registry = query_metrics.query_registry
    registry.reset()
    for d in durations:
        registry.record("SELECT 1", d)
    registry.pool_exhausted_samples = pool_exhausted
    registry.pool_samples = pool_samples
    return query_metrics.summary()


def test_verdict_identifies_a_per_round_trip_cost():
    """High p50 means every statement pays — indexes would not help."""
    verdict = _summary_with([120] * 50)["verdict"]

    assert "round-trip" in verdict
    assert "indexes will not" in verdict


def test_verdict_identifies_pool_queueing():
    """Requests waiting for a connection look exactly like slow queries."""
    verdict = _summary_with([2] * 50, pool_exhausted=7, pool_samples=10)["verdict"]

    assert "queueing for a connection" in verdict


def test_verdict_identifies_a_bad_tail():
    """Healthy baseline, ugly p99 — a few statements are the problem.

    Four slow samples in a hundred, not one: with a nearest-rank percentile a
    single outlier never reaches p99, so a one-in-a-hundred spike is invisible
    here by construction — which is correct, it is not a tail yet.
    """
    verdict = _summary_with([2] * 96 + [900] * 4)["verdict"]

    assert "tail" in verdict


def test_verdict_says_so_when_the_database_is_fine():
    verdict = _summary_with([2] * 50)["verdict"]

    assert "not a bottleneck" in verdict


def test_installing_twice_does_not_double_count(engine):
    """A second install would silently double every duration."""
    query_metrics.install(engine)  # already installed by the fixture
    query_metrics.query_registry.reset()

    _run(engine, [("SELECT 1", None)])

    assert query_metrics.query_registry.total_queries == 1
