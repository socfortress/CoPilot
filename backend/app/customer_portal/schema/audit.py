"""The Customer Portal's Audit Log page (#1298): what happened in a customer's tenant, for its admins.

A deliberately narrow projection of ``audit_log``: an action from an allowlist, who did it (a
portal user by name, the SOC never by name), what it was done to, the status it moved between,
and, for the customer's own users only, the address it came from. The free-text ``details`` and
any other stored value never reach the portal.
"""

from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

AuditCategory = Literal["alerts", "cases", "reports", "users", "account"]
ActorKind = Literal["member", "soc", "other", "unknown"]

PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_MAX = 100
EXPORT_LIMIT = 10000


# ── the switch ────────────────────────────────────────────────────────────────


class PortalAuditSettings(BaseModel):
    customer_code: str
    enabled: bool
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class PortalAuditSettingsResponse(BaseModel):
    settings: PortalAuditSettings
    success: bool
    message: str


class UpdatePortalAuditSettingsRequest(BaseModel):
    enabled: bool


class PortalAuditCustomer(BaseModel):
    customer_code: str
    customer_name: str


class PortalAuditAvailabilityResponse(BaseModel):
    """Whether the caller gets the page: a customer admin of at least one customer that has it on."""

    available: bool
    customers: List[PortalAuditCustomer] = Field(default_factory=list, description="The customers whose log the caller reads")
    success: bool
    message: str


# ── the log ───────────────────────────────────────────────────────────────────


class PortalAuditActor(BaseModel):
    kind: ActorKind = Field(
        ...,
        description="member: one of the customer's portal users, named; soc: the SOC, never named; "
        "other: a portal user of another organization; unknown: no account (a sign-in with an unknown name, a removed user)",
    )
    username: Optional[str] = Field(None, description="Only for a member")


class PortalAuditTarget(BaseModel):
    type: Literal["alert", "case", "report", "user"]
    id: str
    label: Optional[str] = Field(None, description="A report's or a case's name, a user's username")


class PortalAuditEntry(BaseModel):
    id: int
    timestamp: str = Field(..., description="ISO 8601, UTC")
    action: str
    label: str = Field(..., description="What happened, in a few words")
    category: AuditCategory
    actor: PortalAuditActor
    customer_code: Optional[str] = None
    target: Optional[PortalAuditTarget] = None
    from_value: Optional[str] = Field(None, description="A status before the change")
    to_value: Optional[str] = Field(None, description="A status after the change")
    result: Literal["success", "failure", "unknown"]
    source_ip: Optional[str] = Field(None, description="Only for the customer's own users' actions")


class PortalAuditMember(BaseModel):
    id: int
    username: str


class PortalAuditResponse(BaseModel):
    entries: List[PortalAuditEntry]
    total: int
    page: int
    page_size: int
    retention_days: int = Field(..., description="How long the log is kept (AUDIT_LOG_RETENTION_DAYS); 0 = for ever")
    members: List[PortalAuditMember] = Field(default_factory=list, description="The portal users the log can be filtered by")
    success: bool
    message: str
