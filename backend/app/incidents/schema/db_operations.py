from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel

from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import Comment


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


class CaseResponse(BaseModel):
    case: Case
    success: bool
    message: str


class CaseAlertLinkResponse(BaseModel):
    case_alert_link: CaseAlertLink
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
    customer_code_name: str
    source: str


class FieldAndAssetNamesResponse(BaseModel):
    field_names: List[str]
    asset_name: str
    timefield_name: str
    alert_title_name: str
    customer_code_name: str
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
    created_at: datetime


class AlertContextCreate(BaseModel):
    source: str
    context: Dict


class CaseCreate(BaseModel):
    case_name: str
    case_description: str
    case_creation_time: datetime
    case_status: str
    assigned_to: str


class CaseCreateFromAlert(BaseModel):
    alert_id: int


class CaseAlertLinkCreate(BaseModel):
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


class AlertTagCreate(BaseModel):
    alert_id: int
    tag: str


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


class AlertOutResponse(BaseModel):
    alerts: List[AlertOut]
    success: bool
    message: str


class CaseOut(BaseModel):
    id: int
    case_name: str
    case_description: str
    assigned_to: Optional[str] = None
    alerts: Optional[List[AlertOut]] = []
    case_status: Optional[str] = None


class CaseOutResponse(BaseModel):
    cases: List[CaseOut]
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
