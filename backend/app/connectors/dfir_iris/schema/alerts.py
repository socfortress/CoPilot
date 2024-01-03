from typing import Any
from typing import Dict
from typing import List
from typing import Optional

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

class FilterAlertsRequest(BaseModel):
    per_page: int = Field(100, description="The number of alerts to return per page.")
    page: int = Field(1, description="The page number to return.")
    sort: str = Field("desc", description="The sort order for the alerts.")
    alert_title: Optional[str] = Field(None, description="The title of the alert.")
