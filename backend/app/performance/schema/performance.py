from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class LoopLagStats(BaseModel):
    """Event loop scheduling delay - the primary signal for issue #1072."""

    samples: int = Field(..., description="Number of watchdog samples in the current window")
    sample_interval_seconds: float = Field(..., description="How often the watchdog wakes")
    stall_threshold_ms: float = Field(..., description="Drift above which a sample counts as a stall")
    p50_ms: float = Field(..., description="Median scheduling delay - should be near zero on a healthy loop")
    p95_ms: float
    p99_ms: float
    max_ms: float = Field(..., description="Worst scheduling delay observed since the last reset")
    stalls: int = Field(..., description="Samples above the stall threshold")
    total_stalled_ms: float = Field(..., description="Cumulative time the loop was unable to schedule anything")
    stalled_ratio: float = Field(..., description="Fraction of uptime spent blocked (0.0 - 1.0)")


class EndpointTiming(BaseModel):
    method: str
    path: str
    count: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float
    slow_count: int = Field(..., description="Requests over the slow-request threshold")
    error_count: int = Field(..., description="Responses with status >= 500")
    disconnects: int = Field(..., description="Requests where a client disconnect was observed (best effort)")
    stall_hits: int = Field(..., description="Event loop stalls that overlapped a request to this endpoint")
    stalled_ms: float = Field(..., description="Loop-stall time attributed to this endpoint by time overlap")


class RequestTiming(BaseModel):
    request_id: int
    method: str
    path: str
    status_code: int
    duration_ms: float
    started_at: str
    concurrency: int = Field(..., description="Requests in flight when this one completed")
    blocked_ms: float = Field(..., description="Loop-stall time observed while this request was in flight")
    stall_hits: int
    client_disconnected: bool


class InFlightRequest(BaseModel):
    request_id: int
    method: str
    path: str
    age_ms: float
    started_at: str


class LoopStall(BaseModel):
    at: str
    lag_ms: float = Field(..., description="How long the loop was unable to schedule the watchdog")
    window_ms: float
    concurrency: int
    suspects: List[str] = Field(
        ...,
        description="Requests whose lifetime overlapped the stall window - the blocking candidates",
    )


class PerformanceSummaryResponse(BaseModel):
    success: bool
    message: str
    monitoring_enabled: bool
    uptime_seconds: float = Field(..., description="Seconds since process start or last counter reset")
    total_requests: int
    slow_requests: int
    slow_request_threshold_ms: float
    error_requests: int
    client_disconnects: int = Field(..., description="Best effort - see the service docstring for the caveat")
    in_flight: int
    max_concurrency: int
    loop_lag: LoopLagStats
    verdict: str = Field(..., description="Plain-language reading of the loop lag numbers")


class PerformanceEndpointsResponse(BaseModel):
    success: bool
    message: str
    endpoints: List[EndpointTiming]
    dropped_endpoints: int = Field(..., description="Distinct routes not tracked because the endpoint cap was hit")


class PerformanceRequestsResponse(BaseModel):
    success: bool
    message: str
    requests: List[RequestTiming]
    in_flight: List[InFlightRequest]


class PerformanceStallsResponse(BaseModel):
    success: bool
    message: str
    stalls: List[LoopStall]
    total_stalls: int
    total_stalled_ms: float


class PerformanceResetResponse(BaseModel):
    success: bool
    message: str
    reset_at: str
    previous_uptime_seconds: float
    previous_total_requests: int
    previous_max_lag_ms: Optional[float] = None


class QueryStatement(BaseModel):
    statement: str = Field(..., description="Parameterised SQL — no literal values are ever recorded")
    count: int
    total_ms: float
    avg_ms: float
    p95_ms: float
    max_ms: float


class PoolState(BaseModel):
    size: Optional[int] = None
    checked_out: Optional[int] = None
    overflow: Optional[int] = None
    peak_checked_out: Optional[int] = None
    exhausted_samples: Optional[int] = Field(None, description="Snapshots where every connection was in use")
    samples: Optional[int] = None


class DatabaseSummaryResponse(BaseModel):
    success: bool
    message: str
    queries: int
    total_ms: float
    slow_queries: int
    slow_query_threshold_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    pool: PoolState
    dropped_statements: int
    verdict: str = Field(..., description="Which of the three causes the numbers point at")
    top_statements: List[QueryStatement]
