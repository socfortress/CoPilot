from datetime import date
from datetime import timedelta
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field


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
    state_id: Optional[int] = Field(None, description="The ID of the state the case is in.")
    state_name: Optional[str] = Field(None, description="The name of the state the case is in.")
    customer_code: str


class CaseResponse(BaseModel):
    cases: List[CaseModel]
    message: str
    success: bool


class PurgeCaseResponse(BaseModel):
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
    # custom_attributes: Optional[Union[str, None]] = Field(
    #     None,
    #     description="The custom attributes of the case.",
    # )
    custom_attributes: Optional[Dict[str, Union[str, None]]] = Field(
        None,
        description="The custom attributes of the case.",
    )
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
    customer_code: str

    def __init__(self, **data):
        if "custom_attributes" in data and not data["custom_attributes"]:
            data["custom_attributes"] = {"default_key": "no custom attributes found"}  # Replace with your default entry
        super().__init__(**data)


class SingleCaseBody(BaseModel):
    case_id: int


class SingleCaseResponse(BaseModel):
    case: SingleCaseModel
    message: str
    success: bool


class TimeUnit(str, Enum):
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class CaseOlderThanBody(BaseModel):
    older_than: timedelta = Field(..., description="Amount of time to filter cases by")
    time_unit: TimeUnit


class CasesBreachedResponse(BaseModel):
    cases_breached: List[CaseModel]
    message: str
    success: bool


class CaseModificationHistoryItem(BaseModel):
    user: str
    user_id: int
    action: str


class CaseData(BaseModel):
    owner_id: int
    case_soc_id: str
    status_id: int
    case_name: str
    custom_attributes: Optional[str] = None
    open_date: date
    close_date: date
    state_id: int
    case_description: str
    reviewer_id: Optional[int] = None
    closing_note: Optional[str] = None
    case_id: int
    modification_history: Dict[str, CaseModificationHistoryItem]
    classification_id: Optional[int] = None
    review_status_id: Optional[int] = None
    user_id: int
    case_uuid: str
    case_customer: int


class ClosedCaseResponse(BaseModel):
    success: bool
    case: CaseData
    message: str


class ReopenedCaseData(BaseModel):
    owner_id: int
    case_soc_id: str
    status_id: int
    case_name: str
    custom_attributes: Optional[str] = None
    open_date: date
    close_date: Optional[date] = None
    state_id: int
    case_description: str
    reviewer_id: Optional[int] = None
    closing_note: Optional[str] = None
    case_id: int
    modification_history: Dict[str, CaseModificationHistoryItem]
    classification_id: Optional[int] = None
    review_status_id: Optional[int] = None
    user_id: int
    case_uuid: str
    case_customer: int


class ReopenedCaseResponse(BaseModel):
    success: bool
    case: ReopenedCaseData
    message: str
