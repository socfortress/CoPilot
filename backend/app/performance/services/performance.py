"""Read-side aggregation over the in-memory performance registry.

Everything here is a pure projection of `app.middleware.performance`: no DB, no
IO, no third-party calls. Percentiles are computed on read from bounded sample
buffers rather than maintained incrementally, because the buffers are small
(a few hundred floats per endpoint) and computing on read keeps the hot path -
the middleware - as close to free as possible.

Caveat on `client_disconnects`: it is **best effort**. Starlette only surfaces
`http.disconnect` through the receive channel, and a handler that never reads
the request body (every GET) never awaits receive, so the disconnect is not
observed. A cancelled task is also counted. The number is therefore a lower
bound on abandoned navigations - useful as a trend, not as a total.
"""

from datetime import datetime
from datetime import timezone
from typing import List
from typing import Sequence

from app.db.query_metrics import query_registry
from app.db.query_metrics import summary as query_summary
from app.middleware.performance import LAG_SAMPLE_INTERVAL
from app.middleware.performance import LAG_STALL_THRESHOLD_MS
from app.middleware.performance import PERF_MONITOR_ENABLED
from app.middleware.performance import SLOW_REQUEST_MS
from app.middleware.performance import performance_registry
from app.performance.schema.performance import DatabaseSummaryResponse
from app.performance.schema.performance import EndpointTiming
from app.performance.schema.performance import InFlightRequest
from app.performance.schema.performance import LoopLagStats
from app.performance.schema.performance import LoopStall
from app.performance.schema.performance import PerformanceEndpointsResponse
from app.performance.schema.performance import PerformanceRequestsResponse
from app.performance.schema.performance import PerformanceResetResponse
from app.performance.schema.performance import PerformanceStallsResponse
from app.performance.schema.performance import PerformanceSummaryResponse
from app.performance.schema.performance import RequestTiming

SORT_FIELDS = {
    "stalled_ms",
    "stall_hits",
    "avg_ms",
    "p95_ms",
    "max_ms",
    "count",
    "slow_count",
}


def _percentile(samples: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile. Returns 0.0 for an empty sample set."""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = int(round((pct / 100.0) * (len(ordered) - 1)))
    return round(ordered[max(0, min(index, len(ordered) - 1))], 2)


def _iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _build_lag_stats() -> LoopLagStats:
    samples = performance_registry.lag_samples
    uptime = max(performance_registry.uptime_seconds, 1e-9)
    return LoopLagStats(
        samples=len(samples),
        sample_interval_seconds=LAG_SAMPLE_INTERVAL,
        stall_threshold_ms=LAG_STALL_THRESHOLD_MS,
        p50_ms=_percentile(samples, 50),
        p95_ms=_percentile(samples, 95),
        p99_ms=_percentile(samples, 99),
        max_ms=round(performance_registry.max_lag_ms, 2),
        stalls=performance_registry.total_stalls,
        total_stalled_ms=round(performance_registry.total_stalled_ms, 2),
        stalled_ratio=round(performance_registry.total_stalled_ms / 1000.0 / uptime, 4),
    )


def _verdict(lag: LoopLagStats) -> str:
    """Translate the lag numbers into the answer the issue actually asks for."""
    if not PERF_MONITOR_ENABLED:
        return "Monitoring is disabled (PERF_MONITOR_ENABLED=false) - no measurements are being taken."
    if lag.samples == 0:
        return "No samples yet - the watchdog has not completed its first interval."
    if lag.p95_ms < 20 and lag.max_ms < LAG_STALL_THRESHOLD_MS:
        return (
            "Event loop is healthy: it is always able to schedule work promptly. " "Slow pages are not caused by blocking on the backend."
        )
    if lag.stalls == 0:
        return "Minor scheduling delay, no stalls above the threshold. The loop is not being blocked meaningfully."
    return (
        f"Event loop was blocked {lag.stalls} time(s) for {lag.total_stalled_ms:.0f}ms total "
        f"({lag.stalled_ratio * 100:.1f}% of uptime), peaking at {lag.max_ms:.0f}ms. "
        "While blocked, every concurrent request waits regardless of what the client does. "
        "Check /performance/stalls for the endpoints that overlapped each stall."
    )


async def get_performance_summary() -> PerformanceSummaryResponse:
    lag = _build_lag_stats()
    return PerformanceSummaryResponse(
        success=True,
        message="Performance summary retrieved successfully",
        monitoring_enabled=PERF_MONITOR_ENABLED,
        uptime_seconds=round(performance_registry.uptime_seconds, 2),
        total_requests=performance_registry.total_requests,
        slow_requests=performance_registry.total_slow,
        slow_request_threshold_ms=SLOW_REQUEST_MS,
        error_requests=performance_registry.total_errors,
        client_disconnects=performance_registry.total_disconnects,
        in_flight=len(performance_registry.in_flight),
        max_concurrency=performance_registry.max_concurrency,
        loop_lag=lag,
        verdict=_verdict(lag),
    )


async def get_endpoint_timings(limit: int = 50, sort_by: str = "stalled_ms") -> PerformanceEndpointsResponse:
    if sort_by not in SORT_FIELDS:
        sort_by = "stalled_ms"

    rows: List[EndpointTiming] = []
    for stats in performance_registry.endpoints:
        if stats.count == 0:
            continue
        samples = list(stats.samples)
        rows.append(
            EndpointTiming(
                method=stats.method,
                path=stats.path,
                count=stats.count,
                avg_ms=round(stats.total_ms / stats.count, 2),
                p50_ms=_percentile(samples, 50),
                p95_ms=_percentile(samples, 95),
                max_ms=round(stats.max_ms, 2),
                slow_count=stats.slow_count,
                error_count=stats.error_count,
                disconnects=stats.disconnects,
                stall_hits=stats.stall_hits,
                stalled_ms=round(stats.stalled_ms, 2),
            ),
        )

    rows.sort(key=lambda row: getattr(row, sort_by), reverse=True)
    return PerformanceEndpointsResponse(
        success=True,
        # No parentheses inside this f-string: pycodestyle 2.10 mis-tokenises them
        # under Python 3.12 (PEP 701) and reports a bogus E225 on the args below.
        message=f"Endpoint timings retrieved successfully, sorted by {sort_by}",
        endpoints=rows[:limit],
        dropped_endpoints=performance_registry.dropped_endpoints,
    )


async def get_recent_requests(limit: int = 50, min_duration_ms: float = 0.0) -> PerformanceRequestsResponse:
    records = [record for record in performance_registry.recent_requests if record.duration_ms >= min_duration_ms]
    records.reverse()  # newest first

    requests = [
        RequestTiming(
            request_id=record.request_id,
            method=record.method,
            path=record.path,
            status_code=record.status_code,
            duration_ms=round(record.duration_ms, 2),
            started_at=_iso(record.started_wall),
            concurrency=record.concurrency,
            blocked_ms=round(record.blocked_ms, 2),
            stall_hits=record.stall_hits,
            client_disconnected=record.client_disconnected,
        )
        for record in records[:limit]
    ]

    now_mono = performance_registry.started_mono + performance_registry.uptime_seconds
    in_flight = [
        InFlightRequest(
            request_id=entry.request_id,
            method=entry.method,
            path=entry.raw_path,
            age_ms=round((now_mono - entry.started_mono) * 1000.0, 2),
            started_at=_iso(entry.started_wall),
        )
        for entry in performance_registry.in_flight
    ]

    return PerformanceRequestsResponse(
        success=True,
        message="Recent requests retrieved successfully",
        requests=requests,
        in_flight=in_flight,
    )


async def get_loop_stalls(limit: int = 50) -> PerformanceStallsResponse:
    stalls = performance_registry.stalls
    stalls.reverse()  # newest first
    return PerformanceStallsResponse(
        success=True,
        message="Event loop stalls retrieved successfully",
        stalls=[
            LoopStall(
                at=_iso(stall.at_wall),
                lag_ms=round(stall.lag_ms, 2),
                window_ms=round(stall.window_ms, 2),
                concurrency=stall.concurrency,
                suspects=stall.suspects,
            )
            for stall in stalls[:limit]
        ],
        total_stalls=performance_registry.total_stalls,
        total_stalled_ms=round(performance_registry.total_stalled_ms, 2),
    )


async def reset_performance_counters() -> PerformanceResetResponse:
    """Zero the counters so a clean before/after run can be taken.

    In-flight requests stay tracked - see `PerformanceRegistry.reset`.
    """
    previous_uptime = round(performance_registry.uptime_seconds, 2)
    previous_requests = performance_registry.total_requests
    previous_max_lag = round(performance_registry.max_lag_ms, 2)

    performance_registry.reset()
    query_registry.reset()

    return PerformanceResetResponse(
        success=True,
        message="Performance counters reset successfully",
        reset_at=_iso(performance_registry.started_wall),
        previous_uptime_seconds=previous_uptime,
        previous_total_requests=previous_requests,
        previous_max_lag_ms=previous_max_lag,
    )


async def get_database_summary() -> DatabaseSummaryResponse:
    """Per-query timings and pool occupancy (#1072 level 2).

    Sampling the pool on read as well as on the snapshot timer means a manual
    check reflects the moment it was asked, not the last periodic sample.
    """
    query_registry.sample_pool()
    return DatabaseSummaryResponse(
        success=True,
        message="Database metrics retrieved successfully",
        **query_summary(),
    )
