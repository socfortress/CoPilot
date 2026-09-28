"""The Customer Portal Overview in one response (``GET /customer_portal/overview``).

Light projections: the Overview shows a handful of fields per alert and case, so these
are *not* ``AlertOut`` / ``CaseOut`` — no comments, tags, IoCs or linked cases. Each
section carries its own ``error`` so one failing block never blanks the others.
"""

from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from app.customer_portal.schema.ai_reports import PortalAiInsightAlert


def _utc_timestamp(value):
    """Same wire format as ``AlertOut`` / ``CaseOut``, so the portal parses both alike."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return value


class OverviewStatusCounts(BaseModel):
    total: int = 0
    open: int = 0
    in_progress: int = 0
    closed: int = 0


class OverviewAlert(BaseModel):
    id: int
    alert_name: str
    alert_description: Optional[str] = None
    status: str
    alert_creation_time: str
    source: str
    customer_code: str
    asset_names: List[str] = Field(default_factory=list)

    @field_validator("alert_creation_time", mode="before")
    @classmethod
    def format_time(cls, value):
        return _utc_timestamp(value)


class OverviewCase(BaseModel):
    id: int
    case_name: str
    case_description: Optional[str] = None
    case_status: str
    case_creation_time: str
    assigned_to: Optional[str] = None
    customer_code: Optional[str] = None
    alert_count: int = 0

    @field_validator("case_creation_time", mode="before")
    @classmethod
    def format_time(cls, value):
        return _utc_timestamp(value)


class OverviewAlertsSection(BaseModel):
    counts: OverviewStatusCounts = Field(default_factory=OverviewStatusCounts)
    recent: List[OverviewAlert] = Field(default_factory=list)
    error: Optional[str] = None


class OverviewCasesSection(BaseModel):
    counts: OverviewStatusCounts = Field(default_factory=OverviewStatusCounts)
    recent: List[OverviewCase] = Field(default_factory=list)
    error: Optional[str] = None


class OverviewAgentsSection(BaseModel):
    total: int = 0
    online: int = 0
    offline: int = 0
    critical: int = 0
    error: Optional[str] = None


class OverviewAiSection(BaseModel):
    total_reports: int = 0
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    recent: List[PortalAiInsightAlert] = Field(default_factory=list)
    error: Optional[str] = None


class CustomerPortalOverviewResponse(BaseModel):
    alerts: OverviewAlertsSection
    cases: OverviewCasesSection
    agents: OverviewAgentsSection
    ai: OverviewAiSection
    success: bool
    message: str
