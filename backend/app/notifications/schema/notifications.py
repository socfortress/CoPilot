"""
Pydantic schemas for the notification routing module.

The wire-level enums (NotificationTrigger, NotificationChannel,
NotificationSeverity) mirror the v1 string set the database column
accepts. The DB columns themselves are plain strings so adding a new
trigger or channel later is a data-only change — these enums exist
purely for input validation at the API boundary.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


# ---------------------------------------------------------------------------
# Enums (input validation only — DB stores strings)
# ---------------------------------------------------------------------------


class NotificationTrigger(str, Enum):
    """When a route should fire.

    `INVESTIGATION_COMPLETE` covers "tell me whenever the AI finishes,
    regardless of verdict" — useful for low-volume customers who want a
    receipt for every run. `SEVERITY_CRITICAL_OR_HIGH` is the noisier
    feed gated by severity for SOC teams that only want to be paged on
    real findings. More triggers can be added later (true-positive after
    review, IOC accuracy thresholds, etc.) without a schema change.
    """

    INVESTIGATION_COMPLETE = "investigation_complete"
    SEVERITY_CRITICAL_OR_HIGH = "severity_critical_or_high"


class NotificationChannel(str, Enum):
    """Phase 1 delivery channel set.

    SMTP-only intentionally. We considered shipping Slack via raw
    incoming-webhook URLs as a second Phase 1 channel, but Phase 2 will
    handle Slack (and Teams, Outlook, etc.) through Shuffle's hosted MCP
    using the customer's authenticated Slack workspace — at which point
    asking customers to paste a webhook URL into CoPilot is replaced by
    a one-click OAuth picker. To avoid throwaway UI, we ship SMTP only
    for Phase 1 and add `shuffle` as the Phase 2 channel.

    Phase 2 will extend this enum with: SHUFFLE = "shuffle"
    """

    SMTP_EMAIL = "smtp_email"


class NotificationSeverity(str, Enum):
    """Severity tiers, ordered. Mirrors AiAnalystReport.severity_assessment.

    The dispatch service treats `min_severity` inclusively — a route
    with `min_severity="High"` fires on Critical and High but not Medium.
    """

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class DispatchStatus(str, Enum):
    """Result classes for notification_dispatch_log.status."""

    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


# Severity ordering for `min_severity` filtering. Index = priority,
# higher = more severe. Used by the dispatch service to gate routes.
SEVERITY_ORDER: List[str] = [
    NotificationSeverity.INFORMATIONAL.value,
    NotificationSeverity.LOW.value,
    NotificationSeverity.MEDIUM.value,
    NotificationSeverity.HIGH.value,
    NotificationSeverity.CRITICAL.value,
]


# ---------------------------------------------------------------------------
# Routes — request/response shapes
# ---------------------------------------------------------------------------


class NotificationRouteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Human label for the rule (e.g. 'SOC team Slack #alerts').")
    trigger: NotificationTrigger
    channel: NotificationChannel
    destination: str = Field(..., min_length=1, description="Slack incoming-webhook URL or SMTP recipient email (comma-separated for multiple).")
    min_severity: NotificationSeverity = NotificationSeverity.MEDIUM
    format_template: Optional[str] = Field(default=None, description="Optional Jinja override for the message body. Leave empty to use the channel default.")
    enabled: bool = True

    @validator("destination")
    def _strip_destination(cls, v: str) -> str:
        return v.strip()


class NotificationRouteCreate(NotificationRouteBase):
    """Body for POST /customers/{code}/notification_routes."""


class NotificationRouteUpdate(BaseModel):
    """Body for PATCH — every field optional. Mirrors the editable subset
    of NotificationRouteBase."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    trigger: Optional[NotificationTrigger] = None
    channel: Optional[NotificationChannel] = None
    destination: Optional[str] = Field(default=None, min_length=1)
    min_severity: Optional[NotificationSeverity] = None
    format_template: Optional[str] = None
    enabled: Optional[bool] = None


class NotificationRouteRead(NotificationRouteBase):
    id: int
    customer_code: str
    last_dispatched_at: Optional[datetime] = None
    dispatch_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class NotificationRouteListResponse(BaseModel):
    success: bool = True
    message: str = "Routes retrieved"
    routes: List[NotificationRouteRead]


class NotificationRouteResponse(BaseModel):
    success: bool = True
    message: str = "Route saved"
    route: NotificationRouteRead


# ---------------------------------------------------------------------------
# Dispatch log — read-only audit shapes
# ---------------------------------------------------------------------------


class DispatchLogRead(BaseModel):
    id: int
    customer_code: str
    alert_id: int
    route_id: int
    trigger: str
    dispatched_at: datetime
    status: DispatchStatus
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    payload_preview: Optional[str] = None

    class Config:
        orm_mode = True


class DispatchLogListResponse(BaseModel):
    success: bool = True
    message: str = "Dispatch log retrieved"
    entries: List[DispatchLogRead]


# ---------------------------------------------------------------------------
# Dispatch endpoint — the one Talon calls
# ---------------------------------------------------------------------------


class DispatchRequest(BaseModel):
    """Body for POST /notifications/dispatch — what Talon sends after
    completing an investigation. Carries the minimum the dispatch
    service needs to (a) decide which routes match and (b) format the
    message body."""

    customer_code: str = Field(..., description="The alert's customer_code — scopes the route lookup.")
    alert_id: int = Field(..., description="The alert this investigation was for. Used as the idempotency key.")
    trigger: NotificationTrigger = Field(..., description="Which trigger Talon thinks applies. The service still re-validates it against the alert's severity.")
    severity_assessment: NotificationSeverity = Field(..., description="The report's assessed severity — used for `min_severity` filtering.")
    summary: str = Field(..., description="One-paragraph human-readable summary. Renders into the default template.")
    report_url: Optional[str] = Field(default=None, description="Deep link back to the full report in CoPilot.")
    alert_name: Optional[str] = Field(default=None, description="Original alert title for context in the message.")


class DispatchOutcome(BaseModel):
    route_id: int
    route_name: str
    channel: str
    status: DispatchStatus
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None


class DispatchResponse(BaseModel):
    success: bool = True
    message: str = "Dispatch complete"
    routes_matched: int
    dispatched: int
    skipped: int
    failed: int
    outcomes: List[DispatchOutcome]
