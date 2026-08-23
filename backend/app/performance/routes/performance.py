"""Read-only endpoints exposing the runtime performance instrumentation.

Admin-scoped: the payloads enumerate route templates, concrete in-flight paths
and timing characteristics of the deployment, which is reconnaissance material
and not something an analyst or a portal user needs.
"""

from fastapi import APIRouter
from fastapi import Query
from fastapi import Security

from app.auth.utils import AuthHandler
from app.performance.schema.performance import DatabaseSummaryResponse
from app.performance.schema.performance import PerformanceEndpointsResponse
from app.performance.schema.performance import PerformanceRequestsResponse
from app.performance.schema.performance import PerformanceResetResponse
from app.performance.schema.performance import PerformanceStallsResponse
from app.performance.schema.performance import PerformanceSummaryResponse
from app.performance.services.performance import get_database_summary
from app.performance.services.performance import get_endpoint_timings
from app.performance.services.performance import get_loop_stalls
from app.performance.services.performance import get_performance_summary
from app.performance.services.performance import get_recent_requests
from app.performance.services.performance import reset_performance_counters

performance_router = APIRouter()


@performance_router.get(
    "/summary",
    response_model=PerformanceSummaryResponse,
    description="Event loop health, request volume and a plain-language verdict",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def performance_summary_endpoint() -> PerformanceSummaryResponse:
    return await get_performance_summary()


@performance_router.get(
    "/endpoints",
    response_model=PerformanceEndpointsResponse,
    description="Per-endpoint timings, sorted by attributed event loop stall time by default",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def performance_endpoints_endpoint(
    limit: int = Query(50, ge=1, le=500),
    sort_by: str = Query("stalled_ms", description="stalled_ms|stall_hits|avg_ms|p95_ms|max_ms|count|slow_count"),
) -> PerformanceEndpointsResponse:
    return await get_endpoint_timings(limit=limit, sort_by=sort_by)


@performance_router.get(
    "/stalls",
    response_model=PerformanceStallsResponse,
    description="Detected event loop stalls with the requests that overlapped each one",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def performance_stalls_endpoint(
    limit: int = Query(50, ge=1, le=200),
) -> PerformanceStallsResponse:
    return await get_loop_stalls(limit=limit)


@performance_router.get(
    "/requests",
    response_model=PerformanceRequestsResponse,
    description="Recently completed requests plus everything currently in flight",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def performance_requests_endpoint(
    limit: int = Query(50, ge=1, le=500),
    min_duration_ms: float = Query(0.0, ge=0.0, description="Only return requests at least this slow"),
) -> PerformanceRequestsResponse:
    return await get_recent_requests(limit=limit, min_duration_ms=min_duration_ms)


@performance_router.post(
    "/reset",
    response_model=PerformanceResetResponse,
    description="Zero the counters to take a clean before/after measurement",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def performance_reset_endpoint() -> PerformanceResetResponse:
    return await reset_performance_counters()


@performance_router.get(
    "/database",
    response_model=DatabaseSummaryResponse,
    description="Query timings and connection-pool occupancy, with a reading of which cause they point at",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def performance_database_endpoint() -> DatabaseSummaryResponse:
    return await get_database_summary()
