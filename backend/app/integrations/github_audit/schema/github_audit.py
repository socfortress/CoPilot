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


# Request Schemas
class GitHubAuditRequest(BaseModel):
    """Request to run a GitHub organization audit"""

    organization: str = Field(..., description="GitHub organization name to audit")
    include_repos: bool = Field(True, description="Include repository-level audits")
    include_workflows: bool = Field(True, description="Include workflow/actions audits")
    include_members: bool = Field(True, description="Include member/permission audits")
    repo_filter: Optional[List[str]] = Field(None, description="Specific repos to audit (None = all)")


class GitHubCredentialsRequest(BaseModel):
    """GitHub authentication credentials"""

    github_token: str = Field(..., description="GitHub personal access token or app token")
    organization: str = Field(..., description="GitHub organization name")


# Audit Check Result Schemas
class AuditCheck(BaseModel):
    """Individual audit check result"""

    check_id: str = Field(..., description="Unique identifier for the check")
    check_name: str = Field(..., description="Human-readable check name")
    category: str = Field(..., description="Category (e.g., 'repository', 'organization', 'workflow')")
    status: AuditStatus = Field(..., description="Pass/Fail/Warning status")
    severity: SeverityLevel = Field(..., description="Severity if failed")
    description: str = Field(..., description="Description of what was checked")
    recommendation: Optional[str] = Field(None, description="Remediation recommendation if failed")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context/details")
    resource_name: Optional[str] = Field(None, description="Name of resource being checked")
    resource_type: Optional[str] = Field(None, description="Type of resource (repo, org, workflow, etc.)")


class RepositoryAuditResult(BaseModel):
    """Audit results for a single repository"""

    repo_name: str = Field(..., description="Repository name")
    repo_full_name: str = Field(..., description="Full repository name (org/repo)")
    repo_url: str = Field(..., description="Repository URL")
    is_private: bool = Field(..., description="Whether repo is private")
    is_archived: bool = Field(False, description="Whether repo is archived")
    default_branch: str = Field(..., description="Default branch name")
    checks: List[AuditCheck] = Field(default_factory=list, description="Audit checks for this repo")
    passed_count: int = Field(0, description="Number of passed checks")
    failed_count: int = Field(0, description="Number of failed checks")
    warning_count: int = Field(0, description="Number of warning checks")


class OrganizationAuditResult(BaseModel):
    """Audit results for organization-level settings"""

    org_name: str = Field(..., description="Organization name")
    org_url: str = Field(..., description="Organization URL")
    checks: List[AuditCheck] = Field(default_factory=list, description="Organization-level checks")
    passed_count: int = Field(0, description="Number of passed checks")
    failed_count: int = Field(0, description="Number of failed checks")
    warning_count: int = Field(0, description="Number of warning checks")


class WorkflowAuditResult(BaseModel):
    """Audit results for GitHub Actions workflows"""

    repo_name: str = Field(..., description="Repository name")
    workflow_name: str = Field(..., description="Workflow file name")
    workflow_path: str = Field(..., description="Path to workflow file")
    checks: List[AuditCheck] = Field(default_factory=list, description="Workflow checks")


class MemberAuditResult(BaseModel):
    """Audit results for organization members"""

    username: str = Field(..., description="GitHub username")
    role: str = Field(..., description="Member role (admin, member, etc.)")
    has_2fa: Optional[bool] = Field(None, description="Whether 2FA is enabled")
    checks: List[AuditCheck] = Field(default_factory=list, description="Member-specific checks")


class AuditSummary(BaseModel):
    """Summary of the entire audit"""

    organization: str = Field(..., description="Organization audited")
    audit_timestamp: str = Field(..., description="When the audit was performed")
    total_repos_audited: int = Field(0, description="Number of repositories audited")
    total_checks: int = Field(0, description="Total number of checks performed")
    passed_checks: int = Field(0, description="Total passed checks")
    failed_checks: int = Field(0, description="Total failed checks")
    warning_checks: int = Field(0, description="Total warning checks")
    critical_findings: int = Field(0, description="Number of critical severity findings")
    high_findings: int = Field(0, description="Number of high severity findings")
    medium_findings: int = Field(0, description="Number of medium severity findings")
    low_findings: int = Field(0, description="Number of low severity findings")
    score: float = Field(0.0, description="Overall security score (0-100)")
    grade: str = Field("F", description="Letter grade (A-F)")


class GitHubAuditResponse(BaseModel):
    """Full GitHub audit response"""

    success: bool = Field(..., description="Whether the audit completed successfully")
    message: str = Field(..., description="Response message")
    summary: Optional[AuditSummary] = Field(None, description="Audit summary")
    organization_results: Optional[OrganizationAuditResult] = Field(None, description="Org-level results")
    repository_results: List[RepositoryAuditResult] = Field(default_factory=list, description="Per-repo results")
    workflow_results: List[WorkflowAuditResult] = Field(default_factory=list, description="Workflow results")
    member_results: List[MemberAuditResult] = Field(default_factory=list, description="Member results")
    top_findings: List[AuditCheck] = Field(default_factory=list, description="Top priority findings")


class GitHubAuditSummaryResponse(BaseModel):
    """Lightweight summary response"""

    success: bool = Field(..., description="Whether the audit completed successfully")
    message: str = Field(..., description="Response message")
    summary: Optional[AuditSummary] = Field(None, description="Audit summary")
    top_findings: List[AuditCheck] = Field(default_factory=list, description="Top 10 priority findings")


# Stored audit report
class GitHubAuditReport(BaseModel):
    """Stored audit report metadata"""

    id: int = Field(..., description="Report ID")
    organization: str = Field(..., description="Organization audited")
    report_name: str = Field(..., description="Report name")
    audit_timestamp: datetime = Field(..., description="When audit was performed")
    summary: AuditSummary = Field(..., description="Audit summary")
    status: str = Field("completed", description="Report status")
    download_url: str = Field(..., description="URL to download full report")


class GitHubAuditReportListResponse(BaseModel):
    """List of stored audit reports"""

    success: bool = Field(..., description="Whether request succeeded")
    message: str = Field(..., description="Response message")
    reports: List[GitHubAuditReport] = Field(default_factory=list, description="List of reports")
    total_count: int = Field(0, description="Total number of reports")
