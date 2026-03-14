from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class AlertsQueryParams(BaseModel):
    timerange: str = Field("24h", description="Time range (e.g. '1h', '24h', '7d', '1w')")
    page_size: int = Field(50, ge=1, le=1000, description="Number of results per page")
    scroll_id: Optional[str] = Field(None, description="Scroll ID for fetching the next page")


class AlertsQueryResponse(BaseModel):
    alerts: List[Dict[str, Any]]
    total: int
    scroll_id: Optional[str] = None
    page_size: int
    success: bool
    message: str
