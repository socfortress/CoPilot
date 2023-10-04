from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import timedelta
from typing import Union, Dict
from datetime import datetime


class CaseModel(BaseModel):
    access_level: int
    case_close_date: str
    case_description: str
    case_id: int
    case_name: str
    case_open_date: str
    case_soc_id: str
    case_uuid: str
    classification: Optional[str]
    classification_id: Optional[int]
    client_name: str
    opened_by: str
    opened_by_user_id: int
    owner: str
    owner_id: int
    state_id: int
    state_name: str

class CaseResponse(BaseModel):
    cases: List[CaseModel]
    message: str
    success: bool

class ModificationHistoryItem(BaseModel):
    action: str
    user: str
    user_id: int

class SingleCaseModel(BaseModel):
    case_description: str
    case_id: int
    case_name: str
    case_soc_id: str
    case_tags: Optional[str]
    case_uuid: str
    classification: Optional[Union[str, None]]
    classification_id: Optional[Union[int, None]]
    close_date: Optional[Union[str, None]]
    custom_attributes: Optional[Union[str, None]]
    customer_id: int
    customer_name: str
    initial_date: str
    modification_history: Dict[str, ModificationHistoryItem]
    open_by_user: str
    open_by_user_id: int
    open_date: str
    owner: str
    owner_id: int
    protagonists: List[str]
    reviewer: Optional[Union[str, None]]
    reviewer_id: Optional[Union[int, None]]
    state_id: int
    state_name: str
    status_id: int
    status_name: str

class SingleCaseBody(BaseModel):
    case_id: int

class SingleCaseResponse(BaseModel):
    case: SingleCaseModel
    message: str
    success: bool

class TimeUnit(str, Enum):
    HOURS = 'hours'
    DAYS = 'days'
    WEEKS = 'weeks'

class CaseOlderThanBody(BaseModel):
    older_than: timedelta = Field(..., description="Amount of time to filter cases by")
    time_unit: TimeUnit


class CasesBreachedResponse(BaseModel):
    cases_breached: List[CaseModel]
    message: str
    success: bool
