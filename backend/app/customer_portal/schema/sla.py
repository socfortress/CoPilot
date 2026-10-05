from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

# What an end customer sees of the SOC's SLA (#1187).
#
# A deliberately narrow projection of ``app/soc_management/schema/metrics.py``: how
# fast the SOC answered and resolved *this customer's* alerts and cases, against the
# targets promised to them. Never who did it — no analyst names, no per-analyst rows,
# no assignee on anything — and nothing about other tenants or the SOC's internal
# workload. Widening these models is how SOC internals leak into the portal.


class PortalSlaSettings(BaseModel):
    customer_code: str
    enabled: bool
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class PortalSlaSettingsResponse(BaseModel):
    settings: PortalSlaSettings
    success: bool
    message: str


class UpdatePortalSlaSettingsRequest(BaseModel):
    enabled: bool


class PortalSlaAvailabilityResponse(BaseModel):
    customer_code: Optional[str] = None
    enabled: bool
    success: bool
    message: str


class PortalSlaClock(BaseModel):
    met: int = 0
    breached: int = 0
    #: Percentage met of those decided; ``None`` when nothing was decided yet.
    rate: Optional[float] = None


class PortalSlaEntity(BaseModel):
    opened: int = 0
    resolved: int = 0
    acknowledge: PortalSlaClock
    resolve: PortalSlaClock
    #: Medians, seconds.
    time_to_acknowledge: Optional[float] = None
    time_to_resolve: Optional[float] = None


class PortalSlaTarget(BaseModel):
    """One severity's promise and how it was kept."""

    entity: str
    severity: str
    acknowledge_minutes: Optional[int] = None
    resolve_minutes: Optional[int] = None
    business_hours: bool = False
    opened: int = 0
    acknowledge_rate: Optional[float] = None
    resolve_rate: Optional[float] = None
    time_to_resolve: Optional[float] = None


class PortalSlaTrendPoint(BaseModel):
    start: datetime
    opened: int = 0
    resolved: int = 0
    rate: Optional[float] = None


class PortalSlaOpenNow(BaseModel):
    alerts: int = 0
    cases: int = 0
    breached: int = 0
    at_risk: int = 0
    #: Items the SOC is waiting on the customer for; their clocks are stopped.
    waiting_on_you: int = 0


class PortalSlaOverviewResponse(BaseModel):
    enabled: bool = Field(..., description="False when no customer in the caller's scope has the SLA page on — nothing is read")
    customer_codes: List[str] = Field(default_factory=list)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    bucket: Optional[str] = None
    tracking_since: Optional[datetime] = None
    alerts: Optional[PortalSlaEntity] = None
    cases: Optional[PortalSlaEntity] = None
    #: The same figures for the previous period of equal length, for the deltas.
    previous_alerts: Optional[PortalSlaEntity] = None
    previous_cases: Optional[PortalSlaEntity] = None
    targets: List[PortalSlaTarget] = Field(default_factory=list)
    trend: List[PortalSlaTrendPoint] = Field(default_factory=list)
    open_now: Optional[PortalSlaOpenNow] = None
    success: bool = True
    message: str = ""
