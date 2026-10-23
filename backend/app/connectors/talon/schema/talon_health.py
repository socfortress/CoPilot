"""The Talon health dashboard's payload (``GET /api/talon/health``): CoPilot's own view of its Talon
connector, plus talon-analyst's ``/v2/health``, ``/v2/health/history`` and ``/v2/health/metrics``.

Every talon-analyst field is copied into these models by ``services/talon_health.py`` one by one,
checked and bounded: an unknown field is dropped, a field of the wrong type is ``None`` (never the
whole section), and no string longer than its cap reaches the browser. Nothing here can hold the
connector's API key: CoPilot never puts it in, and talon-analyst's strings have user-info stripped
from any URL in them.
"""
from datetime import datetime
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field

ComponentStatus = Literal["ok", "warn", "fail", "off", "unknown"]
OverallStatus = Literal["ok", "degraded", "down", "unknown"]
ComponentGroup = Literal["core", "mcp", "model", "other"]
#: A feature switch as talon-analyst reports it: on/off, or a short word ("shadow", "level 1").
Switch = Union[bool, str, None]


# ── CoPilot's own view ────────────────────────────────────────────────────────


class TalonConnectorState(BaseModel):
    exists: bool = Field(..., description="The Talon row is in the connectors table")
    configured: bool = Field(False, description="An admin has saved a URL (and a key) for it")
    verified: bool = Field(False, description="The connector's last Verify succeeded")
    url: Optional[str] = Field(None, description="The connector's URL, user-info, query and fragment stripped; never the key")


class TalonProbe(BaseModel):
    """One check CoPilot's backend made itself."""

    ok: Optional[bool] = Field(None, description="True passed, False failed, None not checked or not known")
    latency_ms: Optional[float] = None
    status_code: Optional[int] = Field(None, description="Talon's HTTP status, when it answered")
    error: Optional[str] = Field(None, description="A fixed text, plus an exception class name at most")


class TalonJobSummary(BaseModel):
    """The newest row of its kind among the caller's customers: when, which customer, what state."""

    customer_code: str
    status: Optional[str] = None
    at: datetime = Field(..., description="Naive UTC, as the DATETIME columns hold")


class TalonCopilotView(BaseModel):
    connector: TalonConnectorState
    reachable: TalonProbe = Field(..., description="GET {url}/health")
    auth: TalonProbe = Field(..., description="Whether Talon accepted the API key (401 means it is wrong)")
    v2_enabled: bool = Field(..., description='The "Talon v2" setting')
    last_sent: Optional[TalonJobSummary] = Field(None, description="The newest alert CoPilot sent to Talon (talon_investigation_trigger)")
    last_job: Optional[TalonJobSummary] = Field(None, description="The newest ai_analyst_job Talon created")
    last_report: Optional[TalonJobSummary] = Field(None, description="The newest ai_analyst_report Talon wrote")
    jobs_failed_24h: int = 0
    ai_trigger_customers: int = Field(0, description="Customers with the per-customer AI trigger on")
    scope: Literal["deployment", "assigned"] = Field(
        ...,
        description="deployment: an admin's, every customer; assigned: the caller's customers",
    )


# ── talon-analyst's payloads, as CoPilot relays them ──────────────────────────


class TalonHealthComponent(BaseModel):
    id: str
    name: str
    group: ComponentGroup = "other"
    status: ComponentStatus = "unknown"
    latency_ms: Optional[float] = None
    detail: Optional[str] = None
    fix: Optional[str] = None
    checked_at: Optional[str] = None


class TalonHealthModels(BaseModel):
    chat: Optional[str] = None
    investigation: Optional[str] = None


class TalonHealthBudgets(BaseModel):
    """Decimal strings as talon-analyst sends them, never re-computed here. A ceiling is
    ``"unlimited"`` when talon-analyst reported none (its null), and None when it wasn't reported."""

    daily_usd: Optional[str] = None
    monthly_usd: Optional[str] = None
    spent_today_usd: Optional[str] = None
    spent_month_usd: Optional[str] = None


class TalonHealthConfig(BaseModel):
    writeback_mode: Optional[str] = None
    live_customers: List[str] = Field(default_factory=list, description="Only the caller's customers (all of them for an admin)")
    automation_max_level: Optional[int] = None
    automation_policy_source: Optional[str] = None
    v2_api: Switch = None
    action_tools: Switch = None
    endpoint_actions: Switch = None
    intel: Switch = None
    workspace_tools: Switch = None
    chat_browser: Switch = None
    models: TalonHealthModels = Field(default_factory=TalonHealthModels)
    budgets: Optional[TalonHealthBudgets] = Field(None, description="None when talon-analyst reported no budgets")


class TalonHealthData(BaseModel):
    status: OverallStatus = "unknown"
    version: Optional[str] = None
    image_browser: Optional[bool] = None
    uptime_seconds: Optional[float] = None
    checked_at: Optional[str] = None
    components: List[TalonHealthComponent] = Field(default_factory=list)
    config: Optional[TalonHealthConfig] = None


class TalonHistoryBucket(BaseModel):
    t: str
    ok: Optional[int] = None
    warn: Optional[int] = None
    fail: Optional[int] = None


class TalonHistoryData(BaseModel):
    bucket_minutes: Optional[int] = None
    components: Dict[str, List[TalonHistoryBucket]] = Field(default_factory=dict)


class TalonMetricsBucket(BaseModel):
    """``None`` is "no data source", which the UI shows as "no data", never 0."""

    t: str
    investigations_completed: Optional[float] = None
    investigations_failed: Optional[float] = None
    queue_depth_max: Optional[float] = None
    duration_p50_s: Optional[float] = None
    duration_p95_s: Optional[float] = None
    tool_calls: Optional[float] = None
    tool_errors: Optional[float] = None
    model_errors: Optional[float] = None
    cost_usd: Optional[str] = Field(None, description="A decimal string, as talon-analyst sends amounts")


class TalonMetricsData(BaseModel):
    bucket_minutes: Optional[int] = None
    series: List[TalonMetricsBucket] = Field(default_factory=list)


class TalonUpstreamSection(BaseModel):
    """One talon-analyst answer: ``data`` when usable, else ``error`` (a fixed text) and, for an
    older Talon without the route, ``unsupported``."""

    error: Optional[str] = None
    status_code: Optional[int] = None
    unsupported: bool = False


class TalonHealthSection(TalonUpstreamSection):
    data: Optional[TalonHealthData] = None


class TalonHistorySection(TalonUpstreamSection):
    data: Optional[TalonHistoryData] = None


class TalonMetricsSection(TalonUpstreamSection):
    data: Optional[TalonMetricsData] = None


class TalonHealthResponse(BaseModel):
    success: bool
    message: str
    hours: int
    checked_at: datetime = Field(..., description="When CoPilot asked Talon (UTC); up to 30 s old, the cache")
    copilot: TalonCopilotView
    health: TalonHealthSection
    history: TalonHistorySection
    metrics: TalonMetricsSection
