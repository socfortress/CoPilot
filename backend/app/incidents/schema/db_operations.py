from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import validator

from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertToIoC
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
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

    @validator("ioc_type")
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


class AssignedToCase(BaseModel):
    case_id: int
    assigned_to: str


class AlertCreate(BaseModel):
    alert_name: str
    alert_description: str
    status: str
    alert_creation_time: datetime
    customer_code: str
    time_closed: Optional[datetime]
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
    case_creation_time: datetime
    case_status: str
    assigned_to: Optional[str] = None
    id: int


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
    agent_id: Optional[str]
    velociraptor_id: Optional[str]
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
    created_at: datetime


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
    alert_creation_time: datetime
    time_closed: Optional[datetime] = None
    alert_name: str
    alert_description: str
    status: str
    customer_code: str
    source: str
    assigned_to: Optional[str] = None
    comments: List[CommentBase] = []
    assets: List[AssetBase] = []
    tags: List[AlertTagBase] = []
    linked_cases: List[LinkedCaseCreate] = []
    iocs: List[IoCBase] = []


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
    case_creation_time: Optional[datetime] = None
    customer_code: Optional[str] = None
    notification_invoked_number: Optional[int] = 0


class CaseOutResponse(BaseModel):
    cases: List[CaseOut]
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


class NotificationResponse(BaseModel):
    notifications: Optional[List[Notification]] = []
    success: bool
    message: str


class PutNotification(BaseModel):
    customer_code: str
    shuffle_workflow_id: str
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

    @validator("file_name", pre=True, always=True)
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
