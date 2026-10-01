"""Response shapes of the SOC Management dashboard.

They mirror the frozen dataclasses of ``domain/analytics.py`` field for field and are
built from them with ``model_validate(..., from_attributes=True)``, so the domain stays
free of Pydantic and the API contract stays explicit (and visible in OpenAPI).

Durations are seconds; rates are percentages with one decimal, ``None`` when there is
nothing to divide by — "no data" must never render as 0%.
"""

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.soc_management.domain.periods import Bucket
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.sla import SlaState
from app.soc_management.schema.policy import PolicyMatrix


class _FromDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DurationStatsOut(_FromDomain):
    count: int = 0
    mean: Optional[float] = None
    median: Optional[float] = None
    p90: Optional[float] = None


class ComplianceOut(_FromDomain):
    met: int = 0
    breached: int = 0
    at_risk: int = 0
    on_track: int = 0
    paused: int = 0
    not_tracked: int = 0
    decided: int = 0
    rate: Optional[float] = None


class SlaPairOut(_FromDomain):
    ack: ComplianceOut
    resolve: ComplianceOut


class EntityHeadlineOut(_FromDomain):
    opened: int
    resolved: int
    resolved_by_customer: int
    tta: DurationStatsOut
    ttr: DurationStatsOut
    sla: SlaPairOut
    reopened: int


class HeadlineOut(_FromDomain):
    alerts: EntityHeadlineOut
    cases: EntityHeadlineOut
    false_positive_rate: Optional[float] = None
    reviewed_alerts: int
    case_conversion_rate: Optional[float] = None
    escalated_alerts: int


class SeverityRowOut(_FromDomain):
    entity: SlaEntity
    severity: str
    opened: int
    resolved: int
    open_now: int
    breached_now: int
    tta: DurationStatsOut
    ttr: DurationStatsOut
    sla: SlaPairOut


class TrendPointOut(_FromDomain):
    start: datetime
    alerts_opened: int
    alerts_resolved: int
    cases_opened: int
    cases_resolved: int
    sla_rate: Optional[float] = None
    alert_ttr_median: Optional[float] = None


class AnalystRowOut(_FromDomain):
    username: str
    alerts_acknowledged: int
    alerts_resolved: int
    cases_acknowledged: int
    cases_resolved: int
    tta: DurationStatsOut
    ttr: DurationStatsOut
    sla: ComplianceOut
    open_alerts: int
    open_cases: int
    at_risk: int
    breached: int


class RuleRowOut(_FromDomain):
    alert_name: str
    sources: List[str]
    alerts: int
    in_case: int
    reviewed: int
    true_positives: int
    false_positives: int
    false_positive_rate: Optional[float] = None
    noisy: bool
    open_now: int
    ttr: DurationStatsOut
    sla: ComplianceOut
    series: List[int]


class CustomerRowOut(_FromDomain):
    customer_code: str
    customer_name: Optional[str] = None
    alerts: int
    cases: int
    resolved: int
    open_now: int
    breached_now: int
    alert_ttr: DurationStatsOut
    case_ttr: DurationStatsOut
    alert_sla: ComplianceOut
    case_sla: ComplianceOut
    top_rule: Optional[str] = None


class SeverityLoadOut(_FromDomain):
    severity: str
    alerts: int
    cases: int
    breached: int
    at_risk: int


class AssigneeLoadOut(_FromDomain):
    username: str
    alerts: int
    cases: int
    breached: int
    at_risk: int


class WorkloadOut(_FromDomain):
    open_alerts: int
    open_cases: int
    unassigned_alerts: int
    unassigned_cases: int
    oldest_unassigned_at: Optional[datetime] = None
    breached: int
    at_risk: int
    #: Open items whose clocks are stopped while the customer answers.
    waiting_on_customer: int = 0
    by_severity: List[SeverityLoadOut]
    by_assignee: List[AssigneeLoadOut]


class AttentionItemOut(_FromDomain):
    entity: SlaEntity
    id: int
    title: str
    customer_code: Optional[str] = None
    severity: str
    status: str
    assigned_to: Optional[str] = None
    opened_at: datetime
    state: SlaState
    clock: str
    due_at: Optional[datetime] = None
    overdue_seconds: float


class PeriodOut(BaseModel):
    date_from: datetime
    date_to: datetime
    previous_from: datetime
    previous_to: datetime
    bucket: Bucket


class Viewer(BaseModel):
    """Who the dashboard was computed for, so the UI can say what it is showing."""

    username: str
    is_admin: bool
    #: False for analysts: per-analyst tables carry only their own row (#1187).
    sees_all_analysts: bool


class DashboardResponse(BaseModel):
    success: bool = True
    message: str = ""
    generated_at: datetime
    period: PeriodOut
    viewer: Viewer
    #: The customers the figures cover; ``None`` = every customer the caller may see.
    customer_codes: Optional[List[str]] = None
    #: When live tracking began; older items count in volumes only.
    tracking_since: Optional[datetime] = None
    headline: HeadlineOut
    previous: HeadlineOut
    severities: List[SeverityRowOut]
    trends: List[TrendPointOut]
    analysts: List[AnalystRowOut]
    rules: List[RuleRowOut]
    customers: List[CustomerRowOut]
    workload: WorkloadOut
    attention: List[AttentionItemOut]
    #: The targets that apply to the scope shown: the customer's when exactly one
    #: customer is in scope, otherwise the global policy.
    policy: PolicyMatrix


class AttentionResponse(BaseModel):
    success: bool = True
    message: str = ""
    items: List[AttentionItemOut]
    total: int


class SlaClockOut(BaseModel):
    due_at: Optional[datetime] = None
    achieved_at: Optional[datetime] = None
    state: SlaState
    by: Optional[str] = None
    action: Optional[str] = None
    target_minutes: Optional[int] = None


class ItemSlaResponse(BaseModel):
    """One alert's or case's SLA, for the badge on its detail page."""

    success: bool = True
    message: str = ""
    entity: SlaEntity
    id: int
    severity: str
    opened_at: datetime
    tracked: bool
    ack: SlaClockOut
    resolve: SlaClockOut
    first_assigned_at: Optional[datetime] = None
    reopen_count: int = 0
    #: The targets count business hours of ``calendar_timezone``'s calendar.
    business_hours: bool = False
    calendar_timezone: Optional[str] = None
    #: Set while the item waits on the customer; both clocks are stopped.
    paused_at: Optional[datetime] = None
    #: Time spent waiting on the customer so far, the current wait included.
    paused_seconds: int = 0
    generated_at: datetime = Field(description="Server time the states were evaluated at")
