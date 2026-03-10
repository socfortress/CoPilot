from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel


class PackageItem(BaseModel):
    """A single package returned by the Wazuh syscollector packages endpoint."""

    architecture: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    name: Optional[str] = None
    priority: Optional[str] = None
    scan: Optional[Dict[str, Any]] = None
    section: Optional[str] = None
    size: Optional[int] = None
    vendor: Optional[str] = None
    version: Optional[str] = None
    agent_id: Optional[str] = None

    class Config:
        extra = "allow"


class AgentPackagesResponse(BaseModel):
    """Response wrapper for an agent's syscollector packages."""

    packages: List[PackageItem] = []
    total_affected_items: int = 0
    success: bool
    message: str
