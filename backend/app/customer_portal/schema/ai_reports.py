from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

# Read-only projections of the ``ai_analyst_*`` tables for the Customer Portal.
#
# These deliberately expose LESS than app/ai_analyst/schema/ai_analyst.py:
# job ids, template names and agent error messages are internal SOC/agent
# plumbing and never reach an end customer. Keep it that way — widening these
# schemas is how investigation internals leak into the portal.


class PortalAiIoc(BaseModel):
    id: int
    ioc_value: str
    ioc_type: str
    vt_verdict: str
    vt_score: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime


class PortalAiReport(BaseModel):
    id: int
    alert_id: int
    customer_code: str
    severity_assessment: Optional[str] = None
    summary: Optional[str] = None
    report_markdown: Optional[str] = None
    recommended_actions: Optional[str] = None
    created_at: datetime


class PortalAiInvestigation(BaseModel):
    """Investigation lifecycle, without the job id / template / error internals."""

    status: str
    triggered_by: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PortalAiAlertAnalysisResponse(BaseModel):
    alert_id: int
    enabled: bool = Field(True, description="False when the customer's AI report switch is off — no data is read at all")
    has_analysis: bool = Field(..., description="False when no investigation has ever run for this alert")
    investigation: Optional[PortalAiInvestigation] = None
    report: Optional[PortalAiReport] = None
    iocs: List[PortalAiIoc] = Field(default_factory=list)
    success: bool
    message: str


class PortalAiInsightAlert(BaseModel):
    alert_id: int
    alert_name: str
    customer_code: str
    severity_assessment: Optional[str] = None
    summary: Optional[str] = None
    report_created_at: datetime


class PortalAiReportAvailabilityResponse(BaseModel):
    """Answers "should the portal render its AI surfaces for this customer?"

    Called by the portal *before* it decides whether to show the AI Report tab,
    so it stays cheap: no report data, just the switch.
    """

    customer_code: Optional[str] = None
    enabled: bool
    success: bool
    message: str


class PortalAiReportSettings(BaseModel):
    """Operator-facing view of one customer's AI report switch."""

    customer_code: str
    enabled: bool
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class PortalAiReportSettingsResponse(BaseModel):
    settings: PortalAiReportSettings
    success: bool
    message: str


class UpdatePortalAiReportSettingsRequest(BaseModel):
    enabled: bool = Field(..., description="Whether the customer's portal users can see AI analyst findings")


class PortalAiInsightsResponse(BaseModel):
    total_reports: int = Field(..., description="Alerts with at least one AI report, within the user's visibility")
    severity_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Latest-report severity breakdown, keyed by severity label ('Unknown' when unset)",
    )
    recent: List[PortalAiInsightAlert] = Field(default_factory=list)
    success: bool
    message: str
