from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertToIoC
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import CaseComment
from app.incidents.models import CaseDataStore
from app.incidents.models import CaseReportTemplateDataStore
from app.incidents.models import Comment


class DeleteAlertsRequest(BaseModel):
    alert_ids: List[int]


class SocfortressRecommendsWazuhFieldNames(Enum):
    # ! Windows Events
    data_win_eventdata_commandLine = "data_win_eventdata_commandLine"
    data_win_eventdata_parentCommandLine = "data_win_eventdata_parentCommandLine"
    data_win_eventdata_parentImage = "data_win_eventdata_parentImage"
    data_win_eventdata_parentUser = "data_win_eventdata_parentUser"
    data_win_eventdata_image = "data_win_eventdata_image"
    data_win_eventdata_user = "data_win_eventdata_user"
    rule_mitre_id = "rule_mitre_id"
    rule_mitre_tactic = "rule_mitre_tactic"
    rule_mitre_technique = "rule_mitre_technique"
    data_win_eventdata_company = "data_win_eventdata_company"
    data_win_eventdata_hashes = "data_win_eventdata_hashes"
    data_win_eventdata_currentDirectory = "data_win_eventdata_currentDirectory"
    data_win_eventdata_originalFileName = "data_win_eventdata_originalFileName"
    # ! Windows SIGCHECK HITS
    data_Path = "data_Path"
    # ! Extra Use for Within CoPilot
    process_id = "process_id"
    sha256 = "sha256"


class DeleteAlertsResponse(BaseModel):
    message: str
    deleted_alert_ids: List[int]
    not_deleted_alert_ids: List[int]
    success: bool


class SocfortressRecommendsWazuhAssetName(Enum):
    agent_name = "agent_name"


class SocfortressRecommendsWazuhTimeFieldName(Enum):
    timestamp_utc = "timestamp_utc"


class SocfortressRecommendsWazuhAlertTitleName(Enum):
    rule_description = "rule_description"


class SocfortressRecommendsWazuhIoCFieldNames(Enum):
    threat_intel_value = "threat_intel_value"


class SocfortressRecommendsWazuhResponse(BaseModel):
    field_names: List[str]
    asset_name: str
    timefield_name: str
    alert_title_name: str
    ioc_field_names: Optional[List[str]] = None
    source: str
    success: bool
    message: str


class AvailableSourcesResponse(BaseModel):
    source: str
    success: bool
    message: str


class AvailableIndicesResponse(BaseModel):
    indices: List[str]
    success: bool
    message: str


class ConfiguredSourcesResponse(BaseModel):
    sources: List[str]
    success: bool
    message: str


class MappingsResponse(BaseModel):
    available_mappings: List[str]
    success: bool
    message: str


class ValidSources(str, Enum):
    WAZUH = "wazuh"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    IN_PROGRESS = "IN_PROGRESS"


class UpdateAlertStatus(BaseModel):
    alert_id: int
    status: AlertStatus


class BulkUpdateAlertStatus(BaseModel):
    """Apply one status to many alerts (GitHub issue #1098)."""

    alert_ids: List[int]
    status: AlertStatus


class BulkAlertUpdateResponse(BaseModel):
    """Outcome of a bulk alert mutation.

    Mirrors ``DeleteAlertsResponse``: a per-alert failure (missing alert, or a
    customer the caller is not entitled to) is reported as a skipped id rather
    than failing the whole request, so one inaccessible alert in a selection of
    fifty does not discard the other forty-nine.
    """

    message: str
    updated_alert_ids: List[int]
    not_updated_alert_ids: List[int]
    success: bool


class AlertVerdict(str, Enum):
    """Analyst triage verdict. The absence of a verdict (NULL on the alert) is a third,
    meaningful state -- "not yet triaged" -- and is represented by omitting the value
    rather than by a member here."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class FalsePositiveReason(str, Enum):
    """Why an alert was judged a false positive.

    A closed vocabulary on purpose: free-form tags were the pre-existing workaround and
    the reason reporting on false positives was unreliable (GitHub issue #1085). Adding a
    member is a code change, which is what keeps the aggregate counts comparable across
    analysts and across months.
    """

    EXPECTED_ACTIVITY = "EXPECTED_ACTIVITY"
    KNOWN_APPLICATION = "KNOWN_APPLICATION"
    AUTHORIZED_USER = "AUTHORIZED_USER"
    RULE_TOO_SENSITIVE = "RULE_TOO_SENSITIVE"
    OTHER = "OTHER"


# Filter-only sentinel for "no verdict recorded yet". Not an AlertVerdict member and never
# stored -- untriaged is NULL on the column. It exists so a single `verdict` query param can
# express all three states an analyst wants to slice by.
VERDICT_FILTER_UNTRIAGED = "UNTRIAGED"


class UpdateAlertVerdict(BaseModel):
    """Set, change or clear an alert's triage verdict.

    `verdict=None` clears it back to untriaged, which is why the field is Optional rather
    than defaulted -- an analyst who mis-clicked needs a way back to "nobody has judged
    this", and that is not the same as marking it a true positive.
    """

    alert_id: int
    verdict: Optional[AlertVerdict] = None
    verdict_reason: Optional[FalsePositiveReason] = None
    verdict_note: Optional[str] = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def check_reason_matches_verdict(self):
        # A reason only means anything alongside FALSE_POSITIVE. Silently dropping a
        # mismatched one would leave the caller believing it was recorded.
        if self.verdict_reason is not None and self.verdict != AlertVerdict.FALSE_POSITIVE:
            raise ValueError("verdict_reason is only valid when verdict is FALSE_POSITIVE")
        if self.verdict == AlertVerdict.FALSE_POSITIVE and self.verdict_reason is None:
            raise ValueError("verdict_reason is required when verdict is FALSE_POSITIVE")
        return self


class UpdateCaseStatus(BaseModel):
    case_id: int
    status: AlertStatus


class AlertResponse(BaseModel):
    alert: Alert
    success: bool
    message: str


class CommentResponse(BaseModel):
    comment: Comment
    success: bool
    message: str


class CaseCommentResponse(BaseModel):
    comment: CaseComment
    success: bool
    message: str


class AlertContextResponse(BaseModel):
    alert_context: AlertContext
    success: bool
    message: str


class AssetResponse(BaseModel):
    asset: Asset
    success: bool
    message: str


class AlertTagResponse(BaseModel):
    alert_tag: AlertTag
    success: bool
    message: str


class AlertIocValue(str, Enum):
    IP = "IP"
    DOMAIN = "DOMAIN"
    HASH = "HASH"
    URL = "URL"


class AlertIoCCreate(BaseModel):
    alert_id: int
    ioc_value: str
    ioc_type: AlertIocValue
    ioc_description: Optional[str] = None

    @field_validator("ioc_type")
    @classmethod
    def validate_ioc_type(cls, v):
        if v not in AlertIocValue:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid IoC type. Must be one of {', '.join([ioc.value for ioc in AlertIocValue])}",
            )
        return v


class AlertIoCResponse(BaseModel):
    alert_ioc: AlertToIoC
    success: bool
    message: str


class CaseResponse(BaseModel):
    case: Case
    success: bool
    message: str


class CaseAlertLinkResponse(BaseModel):
    case_alert_link: CaseAlertLink
    success: bool
    message: str


class CaseAlertUnLinkResponse(BaseModel):
    success: bool
    message: str
    tasks_orphaned: int = 0


class CaseAlertLinksResponse(BaseModel):
    case_alert_links: List[CaseAlertLink]
    success: bool
    message: str


class AvailableUsersResponse(BaseModel):
    available_users: List[str]
    success: bool
    message: str


class FieldAndAssetNames(BaseModel):
    field_names: List[str]
    asset_name: str
    timefield_name: str
    alert_title_name: str
    ioc_field_names: Optional[List[str]] = None
    source: str


class FieldAndAssetNamesResponse(BaseModel):
    field_names: List[str]
    asset_name: str
    timefield_name: str
    alert_title_name: str
    ioc_field_names: Optional[List[str]] = None
    source: str
    success: bool
    message: str


class AssignedToAlert(BaseModel):
    alert_id: int
    assigned_to: str


class BulkAssignedToAlert(BaseModel):
    """Assign many alerts to one user (GitHub issue #1098)."""

    alert_ids: List[int]
    assigned_to: str


class AssignedToCase(BaseModel):
    case_id: int
    assigned_to: str


class EscalateAlert(BaseModel):
    alert_id: int
    escalated: bool


class EscalateCase(BaseModel):
    case_id: int
    escalated: bool


class AlertCreate(BaseModel):
    alert_name: str
    alert_description: str
    status: str
    alert_creation_time: datetime
    customer_code: str
    time_closed: Optional[datetime] = None
    source: str
    assigned_to: str


class CommentCreate(BaseModel):
    alert_id: int
    comment: str
    user_name: str
    created_at: Optional[datetime] = None


class CommentEdit(BaseModel):
    alert_id: int
    comment_id: int
    comment: str
    user_name: str
    created_at: datetime


class CaseCommentCreate(BaseModel):
    case_id: int
    comment: str
    user_name: str
    created_at: Optional[datetime] = None


class CaseCommentEdit(BaseModel):
    case_id: int
    comment_id: int
    comment: str
    user_name: str
    created_at: datetime


class AlertContextCreate(BaseModel):
    source: str
    context: Dict


class CaseCreate(BaseModel):
    case_name: str
    case_description: str
    case_creation_time: datetime
    case_status: str
    assigned_to: Optional[str] = None
    customer_code: Optional[str] = None


class LinkedCaseCreate(BaseModel):
    case_name: str
    case_description: str
    case_creation_time: str
    case_status: str
    assigned_to: Optional[str] = None
    id: int

    @field_validator("case_creation_time", mode="before")
    @classmethod
    def format_case_creation_time(cls, v):
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return v


class CaseCreateFromAlert(BaseModel):
    alert_id: int


class CaseAlertLinkCreate(BaseModel):
    case_id: int
    alert_id: int


class CaseAlertLinksCreate(BaseModel):
    case_id: int
    alert_ids: List[int]


class CaseAlertUnLink(BaseModel):
    case_id: int
    alert_id: int


class AssetCreate(BaseModel):
    alert_linked: int
    asset_name: str
    alert_context_id: int
    agent_id: Optional[str] = None
    velociraptor_id: Optional[str] = None
    customer_code: str
    index_name: str
    index_id: str


class AlertTagBase(BaseModel):
    tag: str
    id: int


class AlertTagCreate(BaseModel):
    alert_id: int
    tag: str


class AlertTagDelete(BaseModel):
    alert_id: int
    tag_id: int


class AlertIoCDelete(BaseModel):
    alert_id: int
    ioc_id: int


class CommentBase(BaseModel):
    user_name: str
    alert_id: int
    id: int
    comment: str
    created_at: str

    @field_validator("created_at", mode="before")
    @classmethod
    def format_created_at(cls, v):
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return v


class CaseCommentBase(BaseModel):
    user_name: str
    case_id: int
    id: int
    comment: str
    created_at: str

    @field_validator("created_at", mode="before")
    @classmethod
    def format_created_at(cls, v):
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return v


class AssetBase(BaseModel):
    asset_name: str
    agent_id: Optional[str] = None
    customer_code: str
    index_id: str
    alert_linked: int
    id: int
    alert_context_id: int
    velociraptor_id: Optional[str] = None
    index_name: str


class IoCBase(BaseModel):
    value: str
    type: AlertIocValue
    description: Optional[str] = None
    id: int


class AlertOut(BaseModel):
    id: int
    alert_creation_time: str
    time_closed: Optional[str] = None
    alert_name: str
    alert_description: str
    status: str
    customer_code: str
    source: str
    assigned_to: Optional[str] = None
    escalated: bool = False
    verdict: Optional[str] = None
    verdict_reason: Optional[str] = None
    verdict_note: Optional[str] = None
    verdict_by: Optional[str] = None
    verdict_at: Optional[str] = None
    comments: List[CommentBase] = []
    assets: List[AssetBase] = []
    tags: List[AlertTagBase] = []
    linked_cases: List[LinkedCaseCreate] = []
    iocs: List[IoCBase] = []

    @field_validator("alert_creation_time", "time_closed", "verdict_at", mode="before")
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return v


class AlertOutResponse(BaseModel):
    alerts: List[AlertOut]
    total: Optional[int] = None
    open: Optional[int] = None
    in_progress: Optional[int] = None
    closed: Optional[int] = None
    total_filtered: Optional[int] = None
    success: bool
    message: str


class CaseOut(BaseModel):
    id: int
    case_name: str
    case_description: str
    assigned_to: Optional[str] = None
    alerts: Optional[List[AlertOut]] = []
    case_status: Optional[str] = None
    case_creation_time: Optional[str] = None
    customer_code: Optional[str] = None
    notification_invoked_number: Optional[int] = 0
    escalated: bool = False
    comments: List[CaseCommentBase] = []

    @field_validator("case_creation_time", mode="before")
    @classmethod
    def format_case_creation_time(cls, v):
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return v


class CaseOutResponse(BaseModel):
    cases: List[CaseOut]
    total: Optional[int] = None
    open: Optional[int] = None
    in_progress: Optional[int] = None
    closed: Optional[int] = None
    success: bool
    message: str


class CaseNotificationCreate(BaseModel):
    case_id: int


class CaseNotificationResponse(BaseModel):
    success: bool
    message: str


class Notification(BaseModel):
    id: int
    customer_code: str
    shuffle_workflow_id: str
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    notifications: Optional[List[Notification]] = []
    success: bool
    message: str


class PutNotification(BaseModel):
    customer_code: str
    shuffle_workflow_id: str
    enabled: bool


class AITrigger(BaseModel):
    id: int
    customer_code: str
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class AITriggerResponse(BaseModel):
    ai_triggers: Optional[List[AITrigger]] = []
    success: bool
    message: str


class PutAITrigger(BaseModel):
    customer_code: str
    enabled: bool


class CaseDataStoreResponse(BaseModel):
    case_data_store: CaseDataStore
    success: bool
    message: str


class ListCaseDataStoreResponse(BaseModel):
    case_data_store: List[CaseDataStore]
    success: bool
    message: str


class CaseReportTemplateDataStoreResponse(BaseModel):
    case_report_template_data_store: CaseReportTemplateDataStore
    success: bool
    message: str


class CaseDownloadDocxRequest(BaseModel):
    case_id: int
    template_name: str
    file_name: Optional[str] = "case_report.docx"

    @field_validator("file_name", mode="before")
    @classmethod
    def ensure_docx_extension(cls, v):
        if v and not v.endswith(".docx"):
            return f"{v}.docx"
        return v


class CaseReportTemplateDataStoreListResponse(BaseModel):
    case_report_template_data_store: List[str]
    success: bool
    message: str


class DefaultReportTemplateFileNames(Enum):
    CASE_REPORT_JINJA_TEMPLATE = "case_report_jinja_template.docx"


class AlertFilterOptionsResponse(BaseModel):
    sources: List[str]
    assets: List[str]
    tags: List[str]
    statuses: List[str] = [s.value for s in AlertStatus]
    # Verdict vocabulary is served alongside the data-derived options so the UI never
    # hard-codes it. UNTRIAGED is included because it is a selectable filter state even
    # though it is never a stored value.
    verdicts: List[str] = [v.value for v in AlertVerdict] + [VERDICT_FILTER_UNTRIAGED]
    false_positive_reasons: List[str] = [r.value for r in FalsePositiveReason]
    success: bool
    message: str


class FalsePositiveRuleStat(BaseModel):
    """One detection's false-positive record over the window."""

    alert_name: str
    false_positive: int
    reviewed: int
    # None when nothing was reviewed: no rate exists, and 0.0 would read as "clean".
    false_positive_rate: Optional[float] = None


class FalsePositiveCustomerStat(BaseModel):
    customer_code: str
    false_positive: int
    reviewed: int
    false_positive_rate: Optional[float] = None


class VerdictTrendPoint(BaseModel):
    month: str
    false_positive: int
    true_positive: int
    untriaged: int
    false_positive_rate: Optional[float] = None


class VerdictStatsResponse(BaseModel):
    """Aggregate triage-verdict statistics for a window.

    `false_positive_rate` throughout is a percentage of *reviewed* alerts, never of all
    alerts ingested -- otherwise the rate would improve every time triage fell behind.
    `coverage_rate` is what keeps that number in proportion.
    """

    total: int
    reviewed: int
    untriaged: int
    true_positive: int
    false_positive: int
    false_positive_rate: Optional[float] = None
    coverage_rate: Optional[float] = None
    by_reason: List[Tuple[str, int]] = []
    by_alert_name: List[FalsePositiveRuleStat] = []
    by_customer: List[FalsePositiveCustomerStat] = []
    trend: List[VerdictTrendPoint] = []
    success: bool
    message: str


class CaseFilterOptionsResponse(BaseModel):
    statuses: List[str]
    assigned_to: List[str]
    success: bool
    message: str


# ============================================
# Tag Access RBAC Schemas
# ============================================


class AlertTagItem(BaseModel):
    """Single tag item for responses."""

    id: int
    tag: str


class TagAccessCreate(BaseModel):
    """Base schema for creating tag access."""

    tag_ids: List[int]


class UserTagAccessCreate(TagAccessCreate):
    """Assign tags to a user."""

    user_id: int


class RoleTagAccessCreate(TagAccessCreate):
    """Assign tags to a role."""

    role_id: int


class UserTagAccessResponse(BaseModel):
    """Response for user tag access operations."""

    user_id: int
    username: str
    accessible_tags: List[AlertTagItem]
    success: bool
    message: str


class RoleTagAccessResponse(BaseModel):
    """Response for role tag access operations."""

    role_id: int
    role_name: str
    accessible_tags: List[AlertTagItem]
    success: bool
    message: str


class UntaggedAlertBehavior(str, Enum):
    """Options for handling untagged alerts when tag RBAC is enabled."""

    VISIBLE_TO_ALL = "visible_to_all"
    ADMIN_ONLY = "admin_only"
    DEFAULT_TAG = "default_tag"


class TagAccessSettingsUpdate(BaseModel):
    """Update tag access settings."""

    enabled: bool
    untagged_alert_behavior: UntaggedAlertBehavior = UntaggedAlertBehavior.VISIBLE_TO_ALL
    default_tag_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_default_tag(self):
        if self.untagged_alert_behavior == UntaggedAlertBehavior.DEFAULT_TAG and self.default_tag_id is None:
            raise HTTPException(
                status_code=400,
                detail="default_tag_id is required when untagged_alert_behavior is 'default_tag'",
            )
        return self


class TagAccessSettingsItem(BaseModel):
    """Single tag access settings item."""

    enabled: bool
    untagged_alert_behavior: str
    default_tag_id: Optional[int] = None
    default_tag_name: Optional[str] = None


class TagAccessSettingsResponse(BaseModel):
    """Response for tag access settings."""

    settings: TagAccessSettingsItem
    success: bool
    message: str


class UserEffectiveAccessResponse(BaseModel):
    """Shows effective access for a user (combines role + user-specific access)."""

    user_id: int
    username: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    accessible_customers: List[str]
    accessible_tags: List[AlertTagItem]
    is_tag_unrestricted: bool
    tag_rbac_enabled: bool
    success: bool
    message: str


class AllTagsResponse(BaseModel):
    """Response for listing all available tags."""

    tags: List[AlertTagItem]
    success: bool
    message: str
