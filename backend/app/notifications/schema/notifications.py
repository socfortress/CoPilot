"""
Pydantic schemas for the notification routing module.

The wire-level enums (NotificationTrigger, NotificationChannel,
NotificationSeverity) mirror the v1 string set the database column
accepts. The DB columns themselves are plain strings so adding a new
trigger or channel later is a data-only change — these enums exist
purely for input validation at the API boundary.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError as PydanticValidationError
from pydantic import field_validator
from pydantic import model_validator

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

    # Fired by CoPilot itself rather than pushed in by Talon.
    ALERT_CREATED = "alert_created"
    ALERT_ASSIGNED = "alert_assigned"
    CASE_ASSIGNED = "case_assigned"
    CASE_TASK_ASSIGNED = "case_task_assigned"


class NotificationChannel(str, Enum):
    """Delivery channel set.

    Each value maps to a provider in ``app.notifications.channels``. The
    provider owns its own settings shape, validated from the route's ``config``
    column against its declared ``config_schema`` — so adding a channel needs
    neither a migration nor an edit here beyond the enum member.

    ``shuffle`` proxies to Shuffle's hosted MCP: each customer points at their
    own Shuffle org via ``customer_shuffle_integration``, and Shuffle handles the
    OAuth-authenticated downstream app (Slack, Outlook, Teams, Gmail, …). Its
    org stays a real FK column (``shuffle_integration_id``) rather than moving
    into config, so referential integrity and the dispatcher's cross-tenant
    check survive.

    ``webhook`` is a direct HTTP request to any URL the customer chooses, with
    no Shuffle org in the path. By default the dispatcher sends a structured
    JSON object; if the route sets a ``format_template`` its rendered output is
    sent as the raw body instead, so provider-specific shapes (Discord's
    ``{"content": …}``, Slack's ``{"text": …}``) work without a code change.
    """

    SHUFFLE = "shuffle"
    WEBHOOK = "webhook"
    RESEND = "resend"
    TEAMS = "teams"


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


class NotificationScope(str, Enum):
    """Who a route serves.

    CUSTOMER routes deliver to the end customer and carry a customer_code.
    INTERNAL routes deliver to the SOC, belong to no tenant, and are where
    assignment notifications land — an ACME alert assigned to an analyst should
    reach the analyst, not ACME's Slack.
    """

    CUSTOMER = "customer"
    INTERNAL = "internal"


class RecipientMode(str, Enum):
    """Where the destination comes from.

    STATIC reads it from the route's `config`. ASSIGNEE resolves the event's
    assignee to their email at dispatch time, and is only valid on channels
    that declare support for it.
    """

    STATIC = "static"
    ASSIGNEE = "assignee"


class DispatchStatus(str, Enum):
    """Result classes for notification_dispatch_log.status."""

    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


# Triggers whose payload carries AI-written findings.
#
# Dispatches for these are gated on the customer's
# `customer_portal_ai_report_settings` row before anything is delivered to a
# customer-facing route — see `_ai_reports_permitted` in the dispatch service.
# That switch is opt-in (a missing row reads as disabled), so an operator who
# has not explicitly published AI findings to a customer must not have them
# emailed/webhooked out either.
#
# Keep this in sync when adding AI-sourced triggers (`ai_report_reviewed` is
# next, see issue #1007). Non-AI triggers — alert creation, assignment — are
# deliberately NOT listed: the switch governs AI-written content only.
#
# The legacy `severity_critical_or_high` value is included because routes saved
# against an older schema still dispatch through the same AI path; see
# `_trigger_applies`.
# Triggers about *who is working on something* rather than about a customer's
# security posture. They resolve against scope='internal' routes, so assigning
# an ACME alert to an analyst reaches the SOC, never ACME's channel.
INTERNAL_TRIGGERS: frozenset = frozenset(
    {
        "alert_assigned",
        "case_assigned",
        "case_task_assigned",
    },
)


AI_SOURCED_TRIGGERS: frozenset = frozenset(
    {
        "investigation_complete",
        "severity_critical_or_high",
    },
)


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

    @field_validator("trigger", mode="before")
    @classmethod
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

    # Free-form destination hint. Shuffle injects it into the app agent's
    # natural-language input ("send to #soc-alerts"); other channels ignore it
    # and keep it as a human label. Deliberately NOT moved into `config` — it is
    # NOT NULL in the DB and shared across channels, and dropping a seventh
    # column would add migration risk for marginal tidiness.
    destination: Optional[str] = Field(
        default=None,
        description="Destination hint for the Shuffle app (channel name, email address, handle). Unused by other channels.",
    )
    min_severity: NotificationSeverity = NotificationSeverity.MEDIUM
    format_template: Optional[str] = Field(
        default=None,
        description="Optional Jinja override for the message body. Leave empty to use the channel default.",
    )
    enabled: bool = True

    # Which audience this route serves. 'customer' delivers to the end
    # customer; 'internal' delivers to the SOC and belongs to no tenant, which
    # is where assignment notifications go so analyst chatter never reaches a
    # customer's channel.
    scope: NotificationScope = NotificationScope.CUSTOMER

    # 'static' takes the destination from `config`; 'assignee' resolves the
    # event's assignee to their email at dispatch time. Validated against the
    # provider's supports_recipient_modes.
    recipient_mode: RecipientMode = RecipientMode.STATIC

    notify_on_self_assign: bool = Field(
        default=False,
        description="Notify the assignee even when they assigned it to themselves.",
    )

    # Shuffle's org lives on a real FK column rather than inside `config`,
    # because burying an FK in JSON gives up referential integrity and the
    # cross-tenant check the dispatcher performs at send time.
    shuffle_integration_id: Optional[int] = Field(
        default=None,
        description="ID of the customer_shuffle_integration row (required when channel='shuffle').",
    )

    # Per-channel settings, validated against the selected provider's
    # config_schema. Replaces the old column-per-setting scheme, so a new
    # channel needs no migration and no schema edit here.
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Channel-specific settings. Shape is defined by the selected channel's config schema.",
    )

    @field_validator("destination")
    @classmethod
    def _strip_destination(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else v

    @field_validator("config", mode="before")
    @classmethod
    def _parse_config(cls, v):
        """Deserialize the DB's JSON-string column into a dict.

        `config` is a Text column for MySQL/SQLite portability, so an ORM row
        yields a string. Pydantic 2 won't coerce it, and an unparsable value
        must not 500 the list endpoint — fall back to an empty dict so a bad
        row is visible in the UI rather than taking the whole page down.
        """
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            if not v.strip():
                return {}
            try:
                parsed = json.loads(v)
            except ValueError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}


class NotificationRouteCreate(NotificationRouteBase):
    """Body for POST /customers/{code}/notification_routes.

    Write-time validation lives here rather than on the shared base: reads must
    stay lenient so a legacy or hand-edited row surfaces in the UI instead of
    500-ing the whole list.
    """

    @model_validator(mode="after")
    def _validate_against_provider(self):
        """Validate `config` against the channel's declared schema.

        Replaces the hand-written per-channel field checks. Import is local to
        avoid a cycle: the channels package imports this module for the event
        envelope's enums.
        """
        from app.notifications.channels import get_channel

        provider = get_channel(self.channel.value)
        if provider is None:
            raise ValueError(f"Unsupported channel: {self.channel.value}")

        try:
            parsed = provider.config_schema.model_validate(self.config or {})
        except PydanticValidationError as e:
            raise ValueError(f"Invalid config for channel '{self.channel.value}': {e}") from e

        # Normalize back so defaults (e.g. webhook method 'POST') are persisted
        # rather than left implicit.
        self.config = parsed.model_dump()

        if self.recipient_mode.value not in provider.supports_recipient_modes:
            raise ValueError(
                f"Channel '{self.channel.value}' does not support recipient_mode "
                f"'{self.recipient_mode.value}' (supported: {sorted(provider.supports_recipient_modes)})",
            )

        # Channel-specific requirements the generic schema can't express,
        # because they involve columns outside `config`.
        if self.channel == NotificationChannel.SHUFFLE:
            if not self.shuffle_integration_id:
                raise ValueError("shuffle_integration_id is required when channel='shuffle'")
            if not self.config.get("app_id"):
                raise ValueError("config.app_id is required when channel='shuffle'")
            if not self.destination:
                raise ValueError("destination is required when channel='shuffle'")
        elif self.channel == NotificationChannel.WEBHOOK:
            url = self.config.get("url")
            if not url:
                raise ValueError("config.url is required when channel='webhook'")
            if not str(url).lower().startswith(("http://", "https://")):
                raise ValueError("config.url must start with http:// or https://")
        elif self.channel == NotificationChannel.TEAMS:
            url = self.config.get("webhook_url")
            if not url:
                raise ValueError("config.webhook_url is required when channel='teams'")
        elif self.channel == NotificationChannel.RESEND:
            # `to` is only meaningful for static delivery — in assignee mode the
            # address comes from the event, and requiring both would imply the
            # static list is a fallback, which it is not.
            if self.recipient_mode == RecipientMode.STATIC and not self.config.get("to"):
                raise ValueError("config.to is required when channel='resend' and recipient_mode='static'")
        return self


class NotificationRouteUpdate(BaseModel):
    """Body for PATCH — every field optional. Mirrors the editable subset
    of NotificationRouteBase.

    `config` is replaced wholesale rather than merged: a partial merge makes
    "remove this header" impossible to express, and the form always holds the
    complete channel config anyway. It is validated against the *resulting*
    channel in the service layer, which knows the row's current channel when
    the PATCH doesn't change it.
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    trigger: Optional[NotificationTrigger] = None
    channel: Optional[NotificationChannel] = None
    destination: Optional[str] = None
    min_severity: Optional[NotificationSeverity] = None
    format_template: Optional[str] = None
    enabled: Optional[bool] = None
    scope: Optional[NotificationScope] = None
    recipient_mode: Optional[RecipientMode] = None
    notify_on_self_assign: Optional[bool] = None
    shuffle_integration_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class NotificationRouteRead(NotificationRouteBase):
    id: int
    # None on internal-scope routes, which belong to no tenant.
    customer_code: Optional[str] = None
    last_dispatched_at: Optional[datetime] = None
    dispatch_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


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

    @field_validator("shuffle_org_id")
    @classmethod
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
    model_config = ConfigDict(from_attributes=True)


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


class ChannelDescriptor(BaseModel):
    """One delivery channel, as the route form needs to see it.

    `config_schema` is the provider's Pydantic model rendered as JSON Schema.
    The form uses it two ways: to render generic inputs for channels that have
    no hand-written block (so a new channel needs no frontend work), and to
    label/validate the ones that do.
    """

    key: str
    display_name: str
    config_schema: Dict[str, Any]
    supports_recipient_modes: List[str]
    supports_internal_scope: bool
    secret_fields: List[str]


class ResendQuotaResponse(BaseModel):
    """Monthly email usage against Resend's plan limit.

    Deployment-wide by construction: the API key is deployment-wide, so every
    customer's routes draw from the same allowance. `customer_sent` is a
    breakdown for display, never a separate budget.
    """

    success: bool = True
    message: str = "Quota retrieved"
    sent_this_month: int
    limit: int
    customer_sent: Optional[int] = None
    configured: bool = Field(description="Whether the Resend connector has an API key set.")


class ChannelListResponse(BaseModel):
    success: bool = True
    message: str = "Channels retrieved"
    channels: List[ChannelDescriptor]


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
    # Nullable since the log stopped being alert-only — a case-task assignment
    # has no alert. Use entity_type/entity_id for the general case.
    alert_id: Optional[int] = None
    entity_type: str = "alert"
    entity_id: int
    dedupe_key: str
    route_id: int
    trigger: str
    dispatched_at: datetime
    status: DispatchStatus
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    payload_preview: Optional[str] = None
    provider_reference: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


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
    # Vendor-side identifier for the delivery, whatever the channel calls it —
    # Shuffle's execution id today, Resend's message id next. Surfaced in the
    # response so the calling agent (Talon) can cite it in its analyst summary.
    #
    # NOTE: renamed from `shuffle_execution_id`. This is Talon-facing, so if a
    # Talon build still reads the old name it needs updating alongside this.
    provider_reference: Optional[str] = None


class DispatchResponse(BaseModel):
    success: bool = True
    message: str = "Dispatch complete"
    routes_matched: int
    dispatched: int
    skipped: int
    failed: int
    outcomes: List[DispatchOutcome]
