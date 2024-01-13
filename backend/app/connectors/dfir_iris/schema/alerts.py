from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class AlertsResponse(BaseModel):
    alerts: Optional[List[Dict[str, Any]]] = Field([], description="The alerts returned from the search.")
    message: str
    success: bool


class AlertResponse(BaseModel):
    alert: Optional[Dict[str, Any]] = Field({}, description="The alert returned from the search.")
    message: str
    success: bool


class BookmarkedAlertsResponse(BaseModel):
    bookmarked_alerts: Optional[List[Dict[str, Any]]] = Field([], description="The alerts returned from the search.")
    message: str
    success: bool

class DeleteMultipleAlertsRequest(BaseModel):
    alert_ids: List[str] = Field([], description="The IDs of the alerts to delete.")

class DeleteAlertResponse(BaseModel):
    message: str
    success: bool

class SortOrder(Enum):
    desc = "desc"
    asc = "asc"

class FilterAlertsRequest(BaseModel):
    per_page: int = Field(1000, description="The number of alerts to return per page.")
    page: int = Field(1, description="The page number to return.")
    sort: SortOrder = Field(SortOrder.desc, description="The sort order for the alerts.")
    alert_title: Optional[str] = Field(None, description="The title of the alert.")
    alert_owner_id: Optional[int] = Field(None, description="The ID of the alert owner.")


class CaseModificationHistory(BaseModel):
    user: str
    user_id: int
    action: str

class CaseData(BaseModel):
    owner_id: int
    case_soc_id: str
    status_id: int
    case_name: str
    custom_attributes: Optional[Any]
    open_date: str
    close_date: Optional[str]
    state_id: int
    case_description: str
    reviewer_id: Optional[int]
    closing_note: Optional[str]
    case_id: int
    modification_history: Dict[str, CaseModificationHistory]
    classification_id: Optional[int]
    review_status_id: Optional[int]
    user_id: int
    case_uuid: str
    case_customer: int

class CaseCreationResponse(BaseModel):
    success: bool
    case: CaseData
    message: str
