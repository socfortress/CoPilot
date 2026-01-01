from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


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
    """Request schema for syncing vulnerabilities - all fields optional"""

    customer_code: Optional[str] = Field(None, description="Optional customer code filter")
    agent_name: Optional[str] = Field(None, description="Optional specific agent name")
    force_refresh: bool = Field(False, description="Force refresh of existing vulnerabilities")


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


class VulnerabilityDeleteResponse(BaseModel):
    """Response schema for vulnerability delete operations"""

    success: bool
    message: str
    deleted_count: int
    errors: List[str] = []


class VulnerabilitySearchRequest(BaseModel):
    """Request schema for searching vulnerabilities from Wazuh indexer"""

    customer_code: Optional[str] = Field(None, description="Filter by customer code")
    agent_name: Optional[str] = Field(None, description="Filter by agent hostname")
    severity: Optional[str] = Field(None, description="Filter by severity (Critical, High, Medium, Low)")
    page: int = Field(1, description="Page number for pagination", ge=1)
    page_size: int = Field(50, description="Number of vulnerabilities per page", ge=1, le=1000)
    cve_id: Optional[str] = Field(None, description="Filter by specific CVE ID")
    package_name: Optional[str] = Field(None, description="Filter by package name")


class VulnerabilitySearchItem(BaseModel):
    """Individual vulnerability item from search results"""

    cve_id: str
    severity: str
    title: str
    agent_name: str
    customer_code: Optional[str] = None
    references: Optional[str] = None
    detected_at: datetime
    published_at: Optional[datetime] = None
    base_score: Optional[float] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    package_architecture: Optional[str] = None
    epss_score: Optional[str] = None
    epss_percentile: Optional[str] = None


class VulnerabilitySearchResponse(BaseModel):
    """Response schema for vulnerability search results with pagination"""

    vulnerabilities: List[VulnerabilitySearchItem]
    total_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    success: bool
    message: str
    filters_applied: dict = {}


class VulnerabilityReportGenerateRequest(BaseModel):
    customer_code: str
    report_name: Optional[str] = None  # Auto-generate if not provided
    agent_name: Optional[str] = None
    severity: Optional[str] = None
    cve_id: Optional[str] = None
    package_name: Optional[str] = None
    include_epss: bool = False


class VulnerabilityReportResponse(BaseModel):
    id: int
    report_name: str
    customer_code: str
    file_name: str
    file_size: int
    generated_at: datetime
    generated_by: int
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    filters_applied: Dict[str, Any]
    status: str
    download_url: Optional[str] = None


class VulnerabilityReportListResponse(BaseModel):
    reports: List[VulnerabilityReportResponse]
    total_count: int
    success: bool
    message: str


class VulnerabilityReportGenerateResponse(BaseModel):
    success: bool
    message: str
    report: Optional[VulnerabilityReportResponse] = None
    error: Optional[str] = None
