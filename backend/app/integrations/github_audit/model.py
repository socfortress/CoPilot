from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from sqlmodel import JSON
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel
from sqlmodel import Text


class GitHubAuditConfig(SQLModel, table=True):
    """Configuration for GitHub organization security audits per customer."""

    __tablename__ = "github_audit_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False, index=True)

    # GitHub Authentication
    github_token: str = Field(max_length=500, nullable=False, description="GitHub PAT or App token (encrypted)")
    organization: str = Field(max_length=100, nullable=False, description="GitHub organization name")

    # Token metadata
    token_type: str = Field(
        max_length=50,
        default="pat",
        description="Token type: 'pat' (Personal Access Token) or 'app' (GitHub App)",
    )
    token_expires_at: Optional[datetime] = Field(
        nullable=True,
        description="When the token expires (if applicable)",
    )

    # Audit configuration
    enabled: bool = Field(default=True, description="Whether audits are enabled for this org")
    auto_audit_enabled: bool = Field(
        default=False,
        description="Whether to run audits automatically on schedule",
    )
    audit_schedule_cron: Optional[str] = Field(
        max_length=50,
        nullable=True,
        description="Cron expression for scheduled audits (e.g., '0 0 * * 1' for weekly Monday)",
    )

    # Scope options - what to include in audits
    include_repos: bool = Field(default=True, description="Include repository-level audits")
    include_workflows: bool = Field(default=True, description="Include GitHub Actions audits")
    include_members: bool = Field(default=True, description="Include member/permission audits")
    include_archived_repos: bool = Field(default=False, description="Include archived repositories")

    # Filtering
    repo_filter_mode: str = Field(
        max_length=20,
        default="all",
        description="'all', 'include', or 'exclude'",
    )
    repo_filter_list: Optional[List[str]] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="List of repos to include/exclude based on filter_mode",
    )

    # Notification settings
    notify_on_critical: bool = Field(default=True, description="Send notification on critical findings")
    notify_on_high: bool = Field(default=False, description="Send notification on high findings")
    notification_webhook_url: Optional[str] = Field(
        max_length=500,
        nullable=True,
        description="Webhook URL for audit notifications",
    )
    notification_email: Optional[str] = Field(
        max_length=255,
        nullable=True,
        description="Email for audit notifications",
    )

    # Thresholds
    minimum_passing_score: float = Field(
        default=70.0,
        description="Minimum score to consider audit passing (0-100)",
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(max_length=100, nullable=True)
    updated_by: Optional[str] = Field(max_length=100, nullable=True)

    # Last audit info
    last_audit_at: Optional[datetime] = Field(nullable=True, description="When last audit was run")
    last_audit_score: Optional[float] = Field(nullable=True, description="Score from last audit")
    last_audit_grade: Optional[str] = Field(max_length=2, nullable=True, description="Grade from last audit")

    # Relationship to audit reports
    audit_reports: List["GitHubAuditReport"] = Relationship(back_populates="config")


class GitHubAuditReport(SQLModel, table=True):
    """Stored GitHub audit reports."""

    __tablename__ = "github_audit_report"

    id: Optional[int] = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="github_audit_config.id", nullable=False, index=True)
    customer_code: str = Field(max_length=50, nullable=False, index=True)

    # Report identification
    report_name: str = Field(max_length=255, nullable=False)
    organization: str = Field(max_length=100, nullable=False)

    # Audit timing
    audit_started_at: datetime = Field(default_factory=datetime.utcnow)
    audit_completed_at: Optional[datetime] = Field(nullable=True)
    audit_duration_seconds: Optional[float] = Field(nullable=True)

    # Summary data
    total_repos_audited: int = Field(default=0)
    total_checks: int = Field(default=0)
    passed_checks: int = Field(default=0)
    failed_checks: int = Field(default=0)
    warning_checks: int = Field(default=0)
    critical_findings: int = Field(default=0)
    high_findings: int = Field(default=0)
    medium_findings: int = Field(default=0)
    low_findings: int = Field(default=0)
    score: float = Field(default=0.0)
    grade: str = Field(max_length=2, default="F")

    # Status
    status: str = Field(
        max_length=50,
        default="running",
        description="'running', 'completed', 'failed'",
    )
    error_message: Optional[str] = Field(sa_column=Text, nullable=True)

    # Full report data stored as JSON
    full_report: Optional[Dict] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="Complete audit report data",
    )

    # Top findings for quick access
    top_findings: Optional[List[Dict]] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="Top priority findings",
    )

    # Triggered by
    triggered_by: str = Field(
        max_length=50,
        default="manual",
        description="'manual', 'scheduled', 'api'",
    )
    triggered_by_user: Optional[str] = Field(max_length=100, nullable=True)

    # Relationship back to config
    config: GitHubAuditConfig = Relationship(back_populates="audit_reports")


class GitHubAuditCheckExclusion(SQLModel, table=True):
    """Exclusion rules for specific audit checks."""

    __tablename__ = "github_audit_check_exclusion"

    id: Optional[int] = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="github_audit_config.id", nullable=False, index=True)
    customer_code: str = Field(max_length=50, nullable=False, index=True)

    # What to exclude
    check_id: str = Field(
        max_length=100,
        nullable=False,
        description="The check ID to exclude (e.g., 'repo-branch-protection')",
    )
    resource_name: Optional[str] = Field(
        max_length=255,
        nullable=True,
        description="Specific resource to exclude (e.g., repo name). Null = all resources",
    )
    resource_type: Optional[str] = Field(
        max_length=50,
        nullable=True,
        description="Type of resource: 'organization', 'repository', 'workflow', 'member'",
    )

    # Why excluded
    reason: str = Field(sa_column=Text, nullable=False, description="Reason for exclusion")
    approved_by: Optional[str] = Field(max_length=100, nullable=True)
    approved_at: Optional[datetime] = Field(nullable=True)

    # Expiration
    expires_at: Optional[datetime] = Field(
        nullable=True,
        description="When this exclusion expires (null = never)",
    )

    # Metadata
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(max_length=100, nullable=False)


class GitHubAuditBaseline(SQLModel, table=True):
    """Baseline configuration for expected audit results."""

    __tablename__ = "github_audit_baseline"

    id: Optional[int] = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="github_audit_config.id", nullable=False, index=True)
    customer_code: str = Field(max_length=50, nullable=False, index=True)

    # Baseline name
    name: str = Field(max_length=255, nullable=False)
    description: Optional[str] = Field(sa_column=Text, nullable=True)

    # Expected values
    expected_checks: Optional[Dict] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="Expected check results by check_id: {check_id: expected_status}",
    )

    # Baseline from a previous report
    baseline_report_id: Optional[int] = Field(
        foreign_key="github_audit_report.id",
        nullable=True,
        description="Report used to create this baseline",
    )

    # Metadata
    is_active: bool = Field(default=True, description="Whether this is the active baseline")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(max_length=100, nullable=False)
