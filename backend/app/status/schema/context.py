from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

IndicatorStatus = Literal["ok", "warning", "error"]


class SidebarHealthIndicator(BaseModel):
    id: str = Field(description="Stable identifier, e.g. connectors | scheduler | wazuh_catalog")
    status: IndicatorStatus
    label: str
    detail: Optional[str] = None
    count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SidebarContextResponse(BaseModel):
    success: bool = True
    message: str = "Sidebar context loaded"
    current_version: str
    latest_version: Optional[str] = None
    is_outdated: bool = False
    release_url: Optional[str] = None
    indicators: List[SidebarHealthIndicator] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
