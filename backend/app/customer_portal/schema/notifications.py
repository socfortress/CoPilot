"""Request and response shapes for portal user notifications (#1282)."""

from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

NotificationEvent = Literal["alert_created", "waiting_on_you", "case_closed", "report_ready"]
EmailMode = Literal["off", "immediate", "digest"]
Severity = Literal["Informational", "Low", "Medium", "High", "Critical"]

#: How many ids one "mark read" may name.
MAX_MARK_READ_IDS = 200


# ── The per-customer switch (CoPilot operators) ───────────────────────────────


class PortalNotificationSettings(BaseModel):
    customer_code: str
    enabled: bool
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class PortalNotificationSettingsResponse(BaseModel):
    settings: PortalNotificationSettings
    #: Whether SMTP is configured: without it, portal users get the bell only.
    email_configured: bool
    digest_hour_utc: int
    success: bool
    message: str


class UpdatePortalNotificationSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


# ── A portal user's view ──────────────────────────────────────────────────────


class PortalNotificationAvailabilityResponse(BaseModel):
    """Whether the caller's notifications are on, and whether email can reach them."""

    enabled: bool
    email_available: bool
    #: Why email cannot reach the caller, when it cannot.
    email_unavailable_reason: Optional[str] = None
    digest_hour_utc: int
    success: bool
    message: str


class NotificationPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: NotificationEvent
    in_app: bool = True
    email: EmailMode = "off"
    #: New alerts from this severity up. Only for ``alert_created``.
    min_severity: Optional[Severity] = None

    @model_validator(mode="after")
    def severity_only_for_alerts(self):
        if self.min_severity is not None and self.event != "alert_created":
            raise ValueError("min_severity applies to alert_created only")
        return self


class PortalNotificationPreferencesResponse(BaseModel):
    preferences: List[NotificationPreference]
    success: bool
    message: str


class UpdatePortalNotificationPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferences: List[NotificationPreference] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def one_per_event(self):
        events = [pref.event for pref in self.preferences]
        if len(events) != len(set(events)):
            raise ValueError("Each event may appear once")
        return self


class PortalNotificationItem(BaseModel):
    id: int
    customer_code: str
    event: NotificationEvent
    entity_type: str
    entity_id: int
    title: str
    body: Optional[str] = None
    severity: Optional[str] = None
    #: Naive UTC, ISO 8601.
    created_at: str
    read: bool


class PortalNotificationFeedResponse(BaseModel):
    notifications: List[PortalNotificationItem]
    has_more: bool
    unread_count: int
    success: bool
    message: str


class PortalNotificationUnreadResponse(BaseModel):
    unread_count: int
    success: bool
    message: str


class MarkPortalNotificationsReadRequest(BaseModel):
    """Either the ids to mark, or ``all``."""

    model_config = ConfigDict(extra="forbid")

    ids: Optional[List[int]] = Field(default=None, max_length=MAX_MARK_READ_IDS)
    all: bool = False

    @model_validator(mode="after")
    def ids_or_all(self):
        if self.all == (self.ids is not None):
            raise ValueError("Send either ids or all: true")
        return self


class MarkPortalNotificationsReadResponse(BaseModel):
    marked: int
    unread_count: int
    success: bool
    message: str
