from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class AgentScaOverviewItem(BaseModel):
    """Individual SCA item from overview search results"""

    agent_id: str
    agent_name: str
    customer_code: Optional[str] = None
    policy_id: str
    policy_name: str
    description: str
    total_checks: int
    pass_count: int = Field(..., alias="pass")
    fail_count: int = Field(..., alias="fail")
    invalid_count: int = Field(..., alias="invalid")
    score: int
    start_scan: str
    end_scan: str
    references: Optional[str] = None
    hash_file: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class ScaOverviewResponse(BaseModel):
    """Response schema for SCA overview search results with pagination and stats"""

    sca_results: List[AgentScaOverviewItem]
    total_count: int
    # Summary stats across all results
    total_agents: int
    total_policies: int
    average_score: float
    total_checks_all_agents: int
    total_passes_all_agents: int
    total_fails_all_agents: int
    total_invalid_all_agents: int
    # Pagination
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    success: bool
    message: str
    filters_applied: dict = {}


class ScaOverviewRequest(BaseModel):
    """Request schema for searching SCA results across agents"""

    customer_code: Optional[str] = Field(None, description="Filter by customer code")
    agent_name: Optional[str] = Field(None, description="Filter by agent hostname")
    policy_id: Optional[str] = Field(None, description="Filter by specific policy ID")
    policy_name: Optional[str] = Field(None, description="Filter by policy name (partial matching)")
    min_score: Optional[int] = Field(None, description="Filter by minimum score", ge=0, le=100)
    max_score: Optional[int] = Field(None, description="Filter by maximum score", ge=0, le=100)
    page: int = Field(1, description="Page number for pagination", ge=1)
    page_size: int = Field(50, description="Number of results per page", ge=1, le=1000)


class ScaStatsResponse(BaseModel):
    """Response schema for SCA statistics"""

    total_agents_with_sca: int
    total_policies: int
    average_score_across_all: float
    total_checks_all_agents: int
    total_passes_all_agents: int
    total_fails_all_agents: int
    total_invalid_all_agents: int
    by_customer: dict = {}
    success: bool
    message: str


class SCAReportGenerateRequest(BaseModel):
    """Request schema for generating SCA report"""

    customer_code: str
    report_name: Optional[str] = None  # Auto-generate if not provided
    agent_name: Optional[str] = None
    policy_id: Optional[str] = None
    min_score: Optional[int] = Field(None, ge=0, le=100, description="Minimum score filter")
    max_score: Optional[int] = Field(None, ge=0, le=100, description="Maximum score filter")


class SCAReportResponse(BaseModel):
    """Response schema for SCA report details"""

    id: int
    report_name: str
    customer_code: str
    file_name: str
    file_size: int
    generated_at: datetime
    generated_by: int
    total_policies: int
    total_checks: int
    passed_count: int
    failed_count: int
    invalid_count: int
    filters_applied: Dict[str, Any]
    status: str  # processing, completed, failed
    error_message: Optional[str] = None
    download_url: Optional[str] = None


class SCAReportListResponse(BaseModel):
    """Response schema for listing SCA reports"""

    reports: List[SCAReportResponse]
    total_count: int
    success: bool
    message: str


class SCAReportGenerateResponse(BaseModel):
    """Response schema for report generation"""

    success: bool
    message: str
    report: Optional[SCAReportResponse] = None
    error: Optional[str] = None
