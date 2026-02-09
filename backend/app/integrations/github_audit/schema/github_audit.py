from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class AuditStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ==================== Request Schemas ====================


class GitHubAuditRequest(BaseModel):
    """Request to run a GitHub organization audit."""

    organization: str = Field(..., description="GitHub organization name to audit")
    include_repos: bool = Field(True, description="Include repository-level audits")
    include_workflows: bool = Field(True, description="Include workflow/actions audits")
    include_members: bool = Field(True, description="Include member/permission audits")
    repo_filter: Optional[List[str]] = Field(None, description="Specific repos to audit (None = all)")


class GitHubAuditConfigCreate(BaseModel):
    """Request to create a GitHub Audit configuration."""

    customer_code: str = Field(..., max_length=50, description="Customer code")
    github_token: str = Field(..., max_length=500, description="GitHub PAT or App token")
    organization: str = Field(..., max_length=100, description="GitHub organization name")
    token_type: str = Field("pat", max_length=50, description="Token type: 'pat' or 'app'")
    token_expires_at: Optional[datetime] = Field(None, description="When the token expires")
    enabled: bool = Field(True, description="Whether audits are enabled")
    auto_audit_enabled: bool = Field(False, description="Enable scheduled audits")
    audit_schedule_cron: Optional[str] = Field(None, max_length=50, description="Cron schedule")
    include_repos: bool = Field(True, description="Include repository audits")
    include_workflows: bool = Field(True, description="Include workflow audits")
    include_members: bool = Field(True, description="Include member audits")
    include_archived_repos: bool = Field(False, description="Include archived repos")
    repo_filter_mode: str = Field("all", description="'all', 'include', or 'exclude'")
    repo_filter_list: Optional[List[str]] = Field(None, description="Repos to include/exclude")
    notify_on_critical: bool = Field(True, description="Notify on critical findings")
    notify_on_high: bool = Field(False, description="Notify on high findings")
    notification_webhook_url: Optional[str] = Field(None, max_length=500)
    notification_email: Optional[str] = Field(None, max_length=255)
    minimum_passing_score: float = Field(70.0, ge=0, le=100)
    created_by: Optional[str] = Field(None, max_length=100)


class GitHubAuditConfigUpdate(BaseModel):
    """Request to update a GitHub Audit configuration."""

    github_token: Optional[str] = Field(None, max_length=500)
    organization: Optional[str] = Field(None, max_length=100)
    token_type: Optional[str] = Field(None, max_length=50)
    token_expires_at: Optional[datetime] = None
    enabled: Optional[bool] = None
    auto_audit_enabled: Optional[bool] = None
    audit_schedule_cron: Optional[str] = Field(None, max_length=50)
    include_repos: Optional[bool] = None
    include_workflows: Optional[bool] = None
    include_members: Optional[bool] = None
    include_archived_repos: Optional[bool] = None
    repo_filter_mode: Optional[str] = None
    repo_filter_list: Optional[List[str]] = None
    notify_on_critical: Optional[bool] = None
    notify_on_high: Optional[bool] = None
    notification_webhook_url: Optional[str] = Field(None, max_length=500)
    notification_email: Optional[str] = Field(None, max_length=255)
    minimum_passing_score: Optional[float] = Field(None, ge=0, le=100)
    updated_by: Optional[str] = Field(None, max_length=100)


class GitHubAuditExclusionCreate(BaseModel):
    """Request to create a check exclusion."""

    check_id: str = Field(..., max_length=100, description="Check ID to exclude")
    resource_name: Optional[str] = Field(None, max_length=255, description="Specific resource")
    resource_type: Optional[str] = Field(None, max_length=50)
    reason: str = Field(..., description="Reason for exclusion")
    approved_by: Optional[str] = Field(None, max_length=100)
    expires_at: Optional[datetime] = None
    created_by: str = Field(..., max_length=100)


class GitHubAuditExclusionUpdate(BaseModel):
    """Request to update a check exclusion."""

    reason: Optional[str] = None
    approved_by: Optional[str] = Field(None, max_length=100)
    expires_at: Optional[datetime] = None
    enabled: Optional[bool] = None


class GitHubAuditBaselineCreate(BaseModel):
    """Request to create a baseline."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    expected_checks: Optional[Dict[str, str]] = None
    baseline_report_id: Optional[int] = None
    is_active: bool = Field(True)
    created_by: str = Field(..., max_length=100)


class GitHubAuditBaselineUpdate(BaseModel):
    """Request to update a baseline."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== Audit Check Result Schemas ====================


class AuditCheck(BaseModel):
    """Individual audit check result."""

    check_id: str = Field(..., description="Unique identifier for the check")
    check_name: str = Field(..., description="Human-readable check name")
    category: str = Field(..., description="Category (e.g., 'repository', 'organization')")
    status: AuditStatus = Field(..., description="Pass/Fail/Warning status")
    severity: SeverityLevel = Field(..., description="Severity if failed")
    description: str = Field(..., description="Description of what was checked")
    recommendation: Optional[str] = Field(None, description="Remediation recommendation")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    resource_name: Optional[str] = Field(None, description="Name of resource being checked")
    resource_type: Optional[str] = Field(None, description="Type of resource")


class RepositoryAuditResult(BaseModel):
    """Audit results for a single repository."""

    repo_name: str
    repo_full_name: str
    repo_url: str
    is_private: bool
    is_archived: bool = False
    default_branch: str
    checks: List[AuditCheck] = Field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0


class OrganizationAuditResult(BaseModel):
    """Audit results for organization-level settings."""

    org_name: str
    org_url: str
    checks: List[AuditCheck] = Field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0


class WorkflowAuditResult(BaseModel):
    """Audit results for GitHub Actions workflows."""

    repo_name: str
    workflow_name: str
    workflow_path: str
    checks: List[AuditCheck] = Field(default_factory=list)


class MemberAuditResult(BaseModel):
    """Audit results for organization members."""

    username: str
    role: str
    has_2fa: Optional[bool] = None
    checks: List[AuditCheck] = Field(default_factory=list)


class AuditSummary(BaseModel):
    """Summary of the entire audit."""

    organization: str
    audit_timestamp: str
    total_repos_audited: int = 0
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    score: float = 0.0
    grade: str = "F"


# ==================== Response Schemas ====================


class GitHubAuditResponse(BaseModel):
    """Full GitHub audit response."""

    success: bool
    message: str
    summary: Optional[AuditSummary] = None
    organization_results: Optional[OrganizationAuditResult] = None
    repository_results: List[RepositoryAuditResult] = Field(default_factory=list)
    workflow_results: List[WorkflowAuditResult] = Field(default_factory=list)
    member_results: List[MemberAuditResult] = Field(default_factory=list)
    top_findings: List[AuditCheck] = Field(default_factory=list)


class GitHubAuditSummaryResponse(BaseModel):
    """Lightweight summary response."""

    success: bool
    message: str
    summary: Optional[AuditSummary] = None
    top_findings: List[AuditCheck] = Field(default_factory=list)


class GitHubAuditConfigResponse(BaseModel):
    """Response for config operations."""

    success: bool
    message: str
    config: Optional[Any] = None  # GitHubAuditConfig model
    configs: Optional[List[Any]] = None  # List of configs


class GitHubAuditReportListResponse(BaseModel):
    """Response for listing reports."""

    success: bool
    message: str
    reports: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0


class GitHubAuditReportResponse(BaseModel):
    """Response for single report."""

    success: bool
    message: str
    report: Optional[Any] = None  # GitHubAuditReport model


class GitHubAuditExclusionResponse(BaseModel):
    """Response for exclusion operations."""

    success: bool
    message: str
    exclusion: Optional[Any] = None
    exclusions: Optional[List[Any]] = None


class GitHubAuditBaselineResponse(BaseModel):
    """Response for baseline operations."""

    success: bool
    message: str
    baseline: Optional[Any] = None
    baselines: Optional[List[Any]] = None


class AvailableChecksResponse(BaseModel):
    """Response for available checks."""

    success: bool
    message: str
    checks: List[Dict[str, str]] = Field(default_factory=list)
