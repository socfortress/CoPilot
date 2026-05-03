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
    """What kind of event caused this dispatch.

    Currently a single value — `investigation_complete` covers every
    Talon-driven dispatch (one per investigation that reaches the
    write-back step). Severity-based filtering lives entirely in the
    route's `min_severity` field, not here, so the trigger is purely
    an event-type dimension that grows when we add new dispatch
    sources (analyst-review hooks, scheduled-sweep findings,
    IOC-enrichment alerts, etc.).
    """

    INVESTIGATION_COMPLETE = "investigation_complete"


class NotificationChannel(str, Enum):
    """Delivery channel set.

    `shuffle` proxies to Shuffle's hosted MCP — each customer points at
    their own Shuffle Org via `customer_shuffle_integration`, and Shuffle
    handles the OAuth-authenticated downstream app (Slack workspace,
    Outlook tenant, Teams, Gmail, SendGrid, etc.). Routes referencing
    `shuffle` MUST populate the `shuffle_integration_id` + `shuffle_app_id`
    columns. Email, chat, ticketing, and the rest of the catalog all
    flow through this single channel — there's no separate direct SMTP
    path because Shuffle's email apps cover that surface.
    """

    SHUFFLE = "shuffle"


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

    @validator("trigger", pre=True)
    def _coerce_legacy_trigger(cls, v):
        """Coerce legacy `severity_critical_or_high` rows on read.

        Older versions of this schema treated trigger as a severity
        filter; routes saved against that schema have a stale value
        the new enum no longer accepts. Pydantic validates BEFORE the
        enum check when `pre=True`, so we rewrite the legacy value to
        the new event-type value here. The dispatch loop has the same
        backward-compat in `_trigger_applies` for the route-side
        comparison; this is the read-API equivalent.
        """
        if v == "severity_critical_or_high":
            return NotificationTrigger.INVESTIGATION_COMPLETE.value
        return v

    # For SMTP: comma-separated recipient emails. For Shuffle: free-form
    # destination hint (e.g. '#soc-alerts', 'ir@corp.com') that gets
    # injected into Shuffle's natural-language input — Shuffle's app
    # agent figures out how to route it within the authenticated app.
    destination: str = Field(
        ...,
        min_length=1,
        description="Destination hint for the Shuffle app (channel name, email address, handle).",
    )
    min_severity: NotificationSeverity = NotificationSeverity.MEDIUM
    format_template: Optional[str] = Field(
        default=None,
        description="Optional Jinja override for the message body. Leave empty to use the channel default.",
    )
    enabled: bool = True

    # Phase 2: Shuffle routing target. Required when channel='shuffle'.
    # The integration row scopes the dispatch to a specific customer
    # Shuffle org; the app id + name describe which app within that
    # org receives the natural-language input.
    shuffle_integration_id: Optional[int] = Field(
        default=None,
        description="ID of the customer_shuffle_integration row (required when channel='shuffle').",
    )
    shuffle_app_id: Optional[str] = Field(default=None, description="Shuffle app UUID (required when channel='shuffle').")
    shuffle_app_name: Optional[str] = Field(
        default=None,
        description="Human-readable Shuffle app name cached for the UI list (e.g. 'Slack').",
    )

    @validator("destination")
    def _strip_destination(cls, v: str) -> str:
        return v.strip()

    @validator("shuffle_integration_id", always=True)
    def _shuffle_integration_required(cls, v, values):
        if values.get("channel") == NotificationChannel.SHUFFLE and not v:
            raise ValueError("shuffle_integration_id is required when channel='shuffle'")
        return v

    @validator("shuffle_app_id", always=True)
    def _shuffle_app_required(cls, v, values):
        if values.get("channel") == NotificationChannel.SHUFFLE and not v:
            raise ValueError("shuffle_app_id is required when channel='shuffle'")
        return v


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
    # Shuffle target — included on PATCH so admins can re-point a route
    # at a different integration / app without recreating it.
    shuffle_integration_id: Optional[int] = None
    shuffle_app_id: Optional[str] = None
    shuffle_app_name: Optional[str] = None


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


# ---------------------------------------------------------------------------
# Shuffle integrations (Phase 2)
# ---------------------------------------------------------------------------


class ShuffleIntegrationBase(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=128, description="Human label, e.g. 'Acme Production Shuffle'.")
    shuffle_org_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="The customer's Shuffle Org-Id. Sent as the Org-Id header on each dispatch.",
    )
    enabled: bool = True

    @validator("shuffle_org_id")
    def _strip_org(cls, v: str) -> str:
        return v.strip()


class ShuffleIntegrationCreate(ShuffleIntegrationBase):
    """Body for POST /customers/{code}/shuffle_integrations."""


class ShuffleIntegrationUpdate(BaseModel):
    """Body for PATCH — every field optional."""

    display_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    shuffle_org_id: Optional[str] = Field(default=None, min_length=1, max_length=64)
    enabled: Optional[bool] = None


class ShuffleIntegrationRead(ShuffleIntegrationBase):
    id: int
    customer_code: str
    last_used_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ShuffleIntegrationListResponse(BaseModel):
    success: bool = True
    message: str = "Integrations retrieved"
    integrations: List[ShuffleIntegrationRead]


class ShuffleIntegrationResponse(BaseModel):
    success: bool = True
    message: str = "Integration saved"
    integration: ShuffleIntegrationRead


class ShuffleApp(BaseModel):
    """One Shuffle app in the catalog the customer's org has access to.

    Used to populate the route form's app picker. We forward the minimal
    subset Shuffle returns — enough for the UI to render a recognizable
    list and for the form to record the (id, name) pair on submit.
    """

    id: str
    name: str
    description: Optional[str] = None
    large_image: Optional[str] = None


class ShuffleAppListResponse(BaseModel):
    success: bool = True
    message: str = "Apps retrieved"
    apps: List[ShuffleApp]


class ShuffleVerifyResponse(BaseModel):
    success: bool = True
    message: str
    org_id: str
    app_count: Optional[int] = None
    error: Optional[str] = None


class ShuffleOrg(BaseModel):
    """One Shuffle org visible to the deployment's admin Bearer.

    Used to populate the integration form's org-picker dropdown so
    admins don't have to paste UUIDs. Forwards only the fields the UI
    needs — Shuffle's full org payload carries a lot of internal state
    (users, billing, region, sync_config) we don't want leaking
    through. `creator_org` is empty/falsy on top-level orgs and set to
    the parent's UUID on sub-orgs, so the UI can label sub-orgs
    distinctly without an extra round-trip.
    """

    id: str
    name: str
    description: Optional[str] = None
    role: Optional[str] = None
    creator_org: Optional[str] = None


class ShuffleOrgListResponse(BaseModel):
    success: bool = True
    message: str = "Orgs retrieved"
    orgs: List[ShuffleOrg]


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
    shuffle_execution_id: Optional[str] = None

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
    trigger: NotificationTrigger = Field(
        ...,
        description="Which trigger Talon thinks applies. The service still re-validates it against the alert's severity.",
    )
    severity_assessment: NotificationSeverity = Field(
        ...,
        description="The report's assessed severity — used for `min_severity` filtering.",
    )
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
    # Shuffle's POST /apps/{id}/mcp returns this on a successful kickoff.
    # Surfaced in the response so the calling agent (Talon) can include
    # it in its analyst summary if the dispatch went through Shuffle.
    shuffle_execution_id: Optional[str] = None


class DispatchResponse(BaseModel):
    success: bool = True
    message: str = "Dispatch complete"
    routes_matched: int
    dispatched: int
    skipped: int
    failed: int
    outcomes: List[DispatchOutcome]
