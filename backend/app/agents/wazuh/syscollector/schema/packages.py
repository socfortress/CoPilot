from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


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


# ── Wazuh Indexer (OpenSearch) package inventory models ──


class IndexerPackageAgent(BaseModel):
    """Agent info nested inside a Wazuh indexer package document."""

    id: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None


class IndexerPackageDetail(BaseModel):
    """Package info nested inside a Wazuh indexer package document."""

    architecture: Optional[str] = None
    description: Optional[str] = None
    name: Optional[str] = None
    size: Optional[int] = None
    type: Optional[str] = None
    vendor: Optional[str] = None
    version: Optional[str] = None


class IndexerPackageItem(BaseModel):
    """A single document from ``wazuh-states-inventory-packages-*``."""

    index: Optional[str] = Field(None, alias="_index")
    id: Optional[str] = Field(None, alias="_id")
    agent: Optional[IndexerPackageAgent] = None
    package: Optional[IndexerPackageDetail] = None

    class Config:
        populate_by_name = True
        extra = "allow"


class IndexerPackagesResponse(BaseModel):
    """Response wrapper for packages fetched from the Wazuh Indexer."""

    packages: List[IndexerPackageItem] = []
    total: int = 0
    success: bool
    message: str
