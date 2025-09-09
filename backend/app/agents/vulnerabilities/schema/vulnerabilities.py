from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class WazuhVulnerabilityData(BaseModel):
    """Schema for processing raw Wazuh vulnerability data from Elasticsearch"""
    cve_id: str = Field(..., alias="id")
    severity: str
    title: str = Field(..., alias="description")
    references: Optional[str] = Field(None, alias="reference")
    detected_at: datetime
    published_at: Optional[datetime] = None
    base_score: Optional[float] = Field(None, alias="base")
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    package_architecture: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class AgentVulnerabilityOut(BaseModel):
    """Output schema for agent vulnerabilities"""
    id: int
    cve_id: str
    severity: str
    title: str
    references: Optional[str] = None
    status: str
    discovered_at: datetime
    remediated_at: Optional[datetime] = None
    epss_score: Optional[str] = None
    epss_percentile: Optional[str] = None
    package_name: Optional[str] = None
    agent_id: str
    customer_code: Optional[str] = None


class AgentVulnerabilitiesResponse(BaseModel):
    """Response schema for agent vulnerabilities"""
    vulnerabilities: List[AgentVulnerabilityOut]
    success: bool
    message: str
    total_count: int


class VulnerabilitySyncRequest(BaseModel):
    """Request schema for syncing vulnerabilities"""
    customer_code: Optional[str] = None
    agent_name: Optional[str] = None
    force_refresh: bool = False


class VulnerabilitySyncResponse(BaseModel):
    """Response schema for vulnerability sync operations"""
    success: bool
    message: str
    synced_count: int
    errors: List[str] = []


class VulnerabilityStatsResponse(BaseModel):
    """Response schema for vulnerability statistics"""
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    by_customer: dict = {}
    success: bool
    message: str
