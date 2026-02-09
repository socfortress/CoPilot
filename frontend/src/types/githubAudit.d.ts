export enum AuditStatus {
    PASS = "pass",
    FAIL = "fail",
    WARNING = "warning",
    NOT_APPLICABLE = "not_applicable"
}

export enum SeverityLevel {
    CRITICAL = "critical",
    HIGH = "high",
    MEDIUM = "medium",
    LOW = "low",
    INFO = "info"
}

export interface GitHubAuditRequest {
    organization: string
    include_repos?: boolean
    include_workflows?: boolean
    include_members?: boolean
    repo_filter?: string[]
}

export interface AuditCheck {
    check_id: string
    check_name: string
    category: string
    status: AuditStatus
    severity: SeverityLevel
    description: string
    recommendation?: string | null
    details?: Record<string, unknown> | null
    resource_name?: string | null
    resource_type?: string | null
}

export interface RepositoryAuditResult {
    repo_name: string
    repo_full_name: string
    repo_url: string
    is_private: boolean
    is_archived: boolean
    default_branch: string
    checks: AuditCheck[]
    passed_count: number
    failed_count: number
    warning_count: number
}

export interface OrganizationAuditResult {
    org_name: string
    org_url: string
    checks: AuditCheck[]
    passed_count: number
    failed_count: number
    warning_count: number
}

export interface WorkflowAuditResult {
    repo_name: string
    workflow_name: string
    workflow_path: string
    checks: AuditCheck[]
}

export interface MemberAuditResult {
    username: string
    role: string
    has_2fa?: boolean | null
    checks: AuditCheck[]
}

export interface AuditSummary {
    organization: string
    audit_timestamp: string
    total_repos_audited: number
    total_checks: number
    passed_checks: number
    failed_checks: number
    warning_checks: number
    critical_findings: number
    high_findings: number
    medium_findings: number
    low_findings: number
    score: number
    grade: string
}

export interface GitHubAuditResponse {
    success: boolean
    message: string
    summary: AuditSummary | null
    organization_results: OrganizationAuditResult | null
    repository_results: RepositoryAuditResult[]
    workflow_results: WorkflowAuditResult[]
    member_results: MemberAuditResult[]
    top_findings: AuditCheck[]
}

export interface GitHubAuditSummaryResponse {
    success: boolean
    message: string
    summary: AuditSummary | null
    top_findings: AuditCheck[]
}
