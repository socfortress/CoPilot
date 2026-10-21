"""The Customer Portal's Activity page (#1284): what the SOC handled for a customer, broken down.

Every figure covers two windows of the same length: the period asked for and the one just
before it, so the portal can say what changed. Each section carries its own ``error``, so
one failing block never blanks the others.
"""

from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

ActivityRange = Literal["7d", "30d", "90d"]
ACTIVITY_DAYS: Dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}


# ── the switch ────────────────────────────────────────────────────────────────


class PortalActivitySettings(BaseModel):
    customer_code: str
    enabled: bool
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class PortalActivitySettingsResponse(BaseModel):
    settings: PortalActivitySettings
    success: bool
    message: str


class UpdatePortalActivitySettingsRequest(BaseModel):
    enabled: bool


class PortalActivityAvailabilityResponse(BaseModel):
    customer_code: Optional[str] = None
    enabled: bool
    success: bool
    message: str


# ── the page ──────────────────────────────────────────────────────────────────


class ActivityCount(BaseModel):
    """One slice: how many in the period, and in the one before it."""

    key: str = Field(..., description="What the slice is: the source, severity, alert name, asset, tag, reason or case type")
    label: Optional[str] = Field(None, description="How to show the key, when it differs from the key itself")
    count: int = 0
    previous: int = 0


class ActivityTotal(BaseModel):
    count: int = 0
    previous: int = 0


class ActivityAlertsSection(BaseModel):
    opened: ActivityTotal = Field(default_factory=ActivityTotal, description="Alerts that reached the SOC in the period")
    by_source: List[ActivityCount] = Field(default_factory=list, description="Busiest first; what is left over is `other_sources`")
    other_sources: ActivityTotal = Field(default_factory=ActivityTotal)
    by_severity: List[ActivityCount] = Field(default_factory=list, description="Every level, most severe first")
    top_detections: List[ActivityCount] = Field(default_factory=list, description="Alert names, busiest first")
    top_assets: List[ActivityCount] = Field(default_factory=list, description="Alerts per asset, busiest first")
    top_tags: List[ActivityCount] = Field(default_factory=list, description="Alerts per tag, busiest first")
    error: Optional[str] = None


class ActivityVerdictFigures(BaseModel):
    total: int = 0
    reviewed: int = 0
    true_positive: int = 0
    false_positive: int = 0
    untriaged: int = 0
    false_positive_rate: Optional[float] = Field(None, description="Percentage of the *reviewed* alerts; None when none was reviewed")
    coverage_rate: Optional[float] = Field(None, description="Percentage of the alerts the SOC reviewed; None when there were none")


class ActivityNoisyDetection(BaseModel):
    name: str
    false_positives: int
    reviewed: int
    false_positive_rate: Optional[float] = None


class ActivityVerdictsSection(BaseModel):
    current: ActivityVerdictFigures = Field(default_factory=ActivityVerdictFigures)
    previous: ActivityVerdictFigures = Field(default_factory=ActivityVerdictFigures)
    reasons: List[ActivityCount] = Field(default_factory=list, description="Why alerts were false positives, most common first")
    noisy_detections: List[ActivityNoisyDetection] = Field(default_factory=list, description="Alert names with the most false positives")
    error: Optional[str] = None


class ActivityCasesSection(BaseModel):
    opened: ActivityTotal = Field(default_factory=ActivityTotal, description="Cases opened in the period")
    by_type: List[ActivityCount] = Field(default_factory=list, description="From the case name's [INC] / [RFI] / [CONF] / [CTI] prefix")
    by_status: List[ActivityCount] = Field(default_factory=list, description="Where the cases opened in each period stand now")
    error: Optional[str] = None


class PortalActivityResponse(BaseModel):
    enabled: bool = Field(..., description="False when no customer in the caller's scope has the page on: nothing is read")
    customer_codes: List[str] = Field(default_factory=list)
    range: ActivityRange = "30d"
    since: Optional[str] = Field(None, description="Start of the period (inclusive), ISO 8601 UTC")
    until: Optional[str] = Field(None, description="End of the period (exclusive), ISO 8601 UTC")
    previous_since: Optional[str] = Field(None, description="Start of the previous period; it ends at `since`")
    alerts: ActivityAlertsSection = Field(default_factory=ActivityAlertsSection)
    verdicts: ActivityVerdictsSection = Field(default_factory=ActivityVerdictsSection)
    cases: ActivityCasesSection = Field(default_factory=ActivityCasesSection)
    success: bool = True
    message: str = "Activity retrieved"
