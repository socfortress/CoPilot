"""One page of the Customer Portal agents list (``GET /customer_portal/agents``)."""

from typing import List

from pydantic import BaseModel
from pydantic import Field

from app.db.universal_models import Agents


class PortalAgentStats(BaseModel):
    """Counts over every agent in scope, independent of the list filters: they feed the page's cards."""

    total: int = 0
    active: int = 0
    critical: int = 0
    offline: int = 0


class PortalAgentsResponse(BaseModel):
    agents: List[Agents] = Field(default_factory=list, description="The requested page, after filters")
    total: int = Field(0, description="Agents matching the filters, across all pages")
    stats: PortalAgentStats = Field(default_factory=PortalAgentStats)
    statuses: List[str] = Field(default_factory=list, description="Distinct Wazuh statuses in scope, for the status filter")
    os_list: List[str] = Field(default_factory=list, description="Distinct operating systems in scope, for the OS filter")
    success: bool
    message: str
