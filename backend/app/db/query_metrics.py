"""Measure what the database actually costs (#1072, level 2).

Every earlier conclusion about the database was an inference from endpoint
durations: `/api/customers` takes 1.6s and issues three queries, therefore a
query costs ~500ms. That is a guess, and it cannot tell apart three problems
with three different fixes:

* **a slow query** — a missing index, a full scan, an N+1;
* **waiting for a connection** — the pool is saturated and the request queues,
  which looks exactly like a slow query from the outside;
* **baseline round-trip cost** — MySQL in Docker on macOS pays a fixed I/O
  price on *every* statement, however trivial.

The distinction is visible in the shape of the numbers, not in any single one:

| p50 | p99 | reading |
|---|---|---|
| high | high | baseline I/O — every statement pays; indexes will not help |
| low | high | a few bad queries; look at the top of the table |
| low-ish | high, with `pool_exhausted_samples` > 0 | requests queueing for a connection |

So this records per-statement timings *and* samples pool occupancy, and both
land in the same session file as everything else.

Cost on the hot path is two `perf_counter()` calls and a dict update per query.
Statements are already parameterised by SQLAlchemy (`%s` placeholders), so the
text is stable per query shape and safe to use as a key — no literal values, and
nothing user-supplied, ever reaches the log.
"""

import re
import time
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Deque
from typing import Dict
from typing import List

from loguru import logger
from sqlalchemy import event

from app.middleware.performance import _env_float
from app.middleware.performance import _env_int

# A statement slower than this is written to the session log individually.
SLOW_QUERY_MS = _env_float("DB_SLOW_QUERY_MS", 250.0)

# Bounded like every other buffer in this instrumentation.
QUERY_SAMPLES = _env_int("DB_QUERY_SAMPLES", 2000)
MAX_STATEMENTS = _env_int("DB_MAX_STATEMENTS", 300)

_WHITESPACE = re.compile(r"\s+")
_IN_LIST = re.compile(r"IN \(\s*(?:%s|\?)\s*(?:,\s*(?:%s|\?)\s*)+\)", re.IGNORECASE)


def digest(statement: str, limit: int = 220) -> str:
    """A stable, readable key for one query shape.

    `IN (%s, %s, %s)` is collapsed so the same query with a different number of
    bound parameters does not open a new row every time.
    """
    text = _WHITESPACE.sub(" ", statement).strip()
    text = _IN_LIST.sub("IN (...)", text)
    return text[:limit] + ("…" if len(text) > limit else "")


@dataclass
class StatementStats:
    statement: str
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=200))


class QueryRegistry:
    """In-memory, single-process store for query timings and pool occupancy."""

    def __init__(self) -> None:
        self._statements: Dict[str, StatementStats] = {}
        self._durations: Deque[float] = deque(maxlen=QUERY_SAMPLES)
        self.total_queries = 0
        self.total_ms = 0.0
        self.slow_queries = 0
        self.dropped_statements = 0
        self.pool_samples = 0
        self.pool_checked_out_peak = 0
        self.pool_exhausted_samples = 0
        self._pool = None

    # ── recording ────────────────────────────────────────────────────────

    def record(self, statement: str, duration_ms: float) -> None:
        self.total_queries += 1
        self.total_ms += duration_ms
        self._durations.append(duration_ms)

        key = digest(statement)
        stats = self._statements.get(key)
        if stats is None:
            if len(self._statements) >= MAX_STATEMENTS:
                self.dropped_statements += 1
                return
            stats = StatementStats(statement=key)
            self._statements[key] = stats

        stats.count += 1
        stats.total_ms += duration_ms
        stats.samples.append(duration_ms)
        if duration_ms > stats.max_ms:
            stats.max_ms = duration_ms

        if duration_ms >= SLOW_QUERY_MS:
            self.slow_queries += 1
            self._emit_slow(key, duration_ms)

    def _emit_slow(self, statement: str, duration_ms: float) -> None:
        # Imported lazily: this module is imported from db_session, which the
        # performance middleware does not depend on — keep it that way.
        from app.middleware.performance import performance_registry

        performance_registry.record_event(
            "slow_query",
            {"duration_ms": round(duration_ms, 1), "statement": statement},
        )

    def sample_pool(self) -> None:
        """Record how much of the connection pool is in use right now.

        Called from the same periodic task that snapshots everything else, so
        pool pressure is visible on the same timeline as the request latencies
        it would explain.
        """
        pool = self._pool
        if pool is None:
            return
        try:
            checked_out = pool.checkedout()
            capacity = pool.size() + max(pool.overflow(), 0)
        except Exception:  # noqa: BLE001 — instrumentation must never raise
            return

        self.pool_samples += 1
        if checked_out > self.pool_checked_out_peak:
            self.pool_checked_out_peak = checked_out
        if capacity and checked_out >= capacity:
            self.pool_exhausted_samples += 1

    def reset(self) -> None:
        pool = self._pool
        self.__init__()  # noqa: PLC2801 — deliberately reuses the field defaults
        self._pool = pool

    # ── reading ──────────────────────────────────────────────────────────

    @property
    def durations(self) -> List[float]:
        return list(self._durations)

    @property
    def statements(self) -> List[StatementStats]:
        return list(self._statements.values())

    def pool_state(self) -> Dict[str, Any]:
        pool = self._pool
        if pool is None:
            return {}
        try:
            return {
                "size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": max(pool.overflow(), 0),
                "peak_checked_out": self.pool_checked_out_peak,
                "exhausted_samples": self.pool_exhausted_samples,
                "samples": self.pool_samples,
            }
        except Exception:  # noqa: BLE001
            return {}


query_registry = QueryRegistry()


def install(async_engine) -> None:
    """Attach the timing listeners. Safe to call more than once.

    Events live on the *sync* engine even for an async one — SQLAlchemy runs the
    DBAPI calls in a greenlet, and that is where the cursor events fire.
    """
    sync_engine = getattr(async_engine, "sync_engine", async_engine)
    if getattr(sync_engine, "_copilot_query_metrics", False):
        return

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        # A stack, not a scalar: a connection can nest executions.
        conn.info.setdefault("_copilot_query_start", []).append(time.perf_counter())

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        stack = conn.info.get("_copilot_query_start")
        if not stack:
            return
        started = stack.pop()
        try:
            query_registry.record(statement, (time.perf_counter() - started) * 1000.0)
        except Exception as exc:  # noqa: BLE001 — never fail a query over metrics
            logger.warning(f"DB query metrics failed to record: {exc}")

    query_registry._pool = async_engine.pool
    sync_engine._copilot_query_metrics = True
    logger.info(f"DB query metrics installed (slow-query threshold {SLOW_QUERY_MS:.0f}ms)")


def percentile(samples: List[float], pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = int(round((pct / 100.0) * (len(ordered) - 1)))
    return round(ordered[max(0, min(index, len(ordered) - 1))], 2)


def summary(top: int = 12) -> Dict[str, Any]:
    """The whole point: numbers shaped so the three causes are distinguishable."""
    durations = query_registry.durations
    statements = [s for s in query_registry.statements if s.count]
    statements.sort(key=lambda s: s.total_ms, reverse=True)

    p50 = percentile(durations, 50)
    p99 = percentile(durations, 99)

    if not durations:
        verdict = "No queries recorded yet."
    elif p50 >= 50:
        verdict = (
            f"Every statement pays ~{p50:.0f}ms (p50), so the cost is per-round-trip, not per-query — "
            "indexes will not move this. Look at where the database runs, not at the SQL."
        )
    elif query_registry.pool_exhausted_samples:
        verdict = (
            f"The pool was fully checked out on {query_registry.pool_exhausted_samples} of "
            f"{query_registry.pool_samples} samples: requests are queueing for a connection, "
            "which looks like a slow query but is not one."
        )
    elif p99 >= 250:
        verdict = f"Baseline is healthy (p50 {p50:.0f}ms) but the tail is not (p99 {p99:.0f}ms) — a few statements are the problem."
    else:
        verdict = f"Database is not a bottleneck: p50 {p50:.0f}ms, p99 {p99:.0f}ms."

    return {
        "queries": query_registry.total_queries,
        "total_ms": round(query_registry.total_ms, 1),
        "slow_queries": query_registry.slow_queries,
        "slow_query_threshold_ms": SLOW_QUERY_MS,
        "p50_ms": p50,
        "p95_ms": percentile(durations, 95),
        "p99_ms": p99,
        "max_ms": round(max(durations), 2) if durations else 0.0,
        "pool": query_registry.pool_state(),
        "dropped_statements": query_registry.dropped_statements,
        "verdict": verdict,
        "top_statements": [
            {
                "statement": s.statement,
                "count": s.count,
                "total_ms": round(s.total_ms, 1),
                "avg_ms": round(s.total_ms / s.count, 2),
                "p95_ms": percentile(list(s.samples), 95),
                "max_ms": round(s.max_ms, 2),
            }
            for s in statements[:top]
        ],
    }
