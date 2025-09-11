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
