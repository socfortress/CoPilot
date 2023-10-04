from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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

