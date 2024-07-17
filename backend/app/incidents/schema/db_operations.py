from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from fastapi import HTTPException

from pydantic import BaseModel, validator


class MappingsResponse(BaseModel):
    available_mappings: List[str]
    success: bool
    message: str


class ValidSources(str, Enum):
    WAZUH = "wazuh"


class FieldAndAssetNames(BaseModel):
    field_names: List[str]
    asset_name: str
    timefield_name: str
    alert_title_name: str
    source: ValidSources

class FieldAndAssetNamesResponse(BaseModel):
    field_names: List[str]
    asset_name: str
    timefield_name: str
    alert_title_name: str
    source: ValidSources
    success: bool
    message: str


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


class CaseOut(BaseModel):
    id: int
    case_name: str
    case_description: str
    assigned_to: str
    alerts: List[AlertOut]
