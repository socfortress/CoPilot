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

// ==================== Request Types ====================

export interface GitHubAuditRequest {
    organization: string
    include_repos?: boolean
    include_workflows?: boolean
    include_members?: boolean
    repo_filter?: string[]
}

export interface GitHubAuditConfigCreate {
    customer_code: string
    github_token: string
    organization: string
    token_type?: string
    token_expires_at?: string | null
    enabled?: boolean
    auto_audit_enabled?: boolean
    audit_schedule_cron?: string | null
    include_repos?: boolean
    include_workflows?: boolean
    include_members?: boolean
    include_archived_repos?: boolean
    repo_filter_mode?: string
    repo_filter_list?: string[] | null
    notify_on_critical?: boolean
    notify_on_high?: boolean
    notification_webhook_url?: string | null
    notification_email?: string | null
    minimum_passing_score?: number
    created_by?: string | null
}

export interface GitHubAuditConfigUpdate {
    github_token?: string | null
    organization?: string | null
    token_type?: string | null
    token_expires_at?: string | null
    enabled?: boolean | null
    auto_audit_enabled?: boolean | null
    audit_schedule_cron?: string | null
    include_repos?: boolean | null
    include_workflows?: boolean | null
    include_members?: boolean | null
    include_archived_repos?: boolean | null
    repo_filter_mode?: string | null
    repo_filter_list?: string[] | null
    notify_on_critical?: boolean | null
    notify_on_high?: boolean | null
    notification_webhook_url?: string | null
    notification_email?: string | null
    minimum_passing_score?: number | null
    updated_by?: string | null
}

export interface GitHubAuditExclusionCreate {
    check_id: string
    resource_name?: string | null
    resource_type?: string | null
    reason: string
    approved_by?: string | null
    expires_at?: string | null
    created_by: string
}

export interface GitHubAuditExclusionUpdate {
    reason?: string | null
    approved_by?: string | null
    expires_at?: string | null
    enabled?: boolean | null
}

export interface GitHubAuditBaselineCreate {
    name: string
    description?: string | null
    expected_checks?: Record<string, string> | null
    baseline_report_id?: number | null
    is_active?: boolean
    created_by: string
}

export interface GitHubAuditBaselineUpdate {
    name?: string | null
    description?: string | null
    is_active?: boolean | null
}

// ==================== Model Types ====================

export interface GitHubAuditConfig {
    id: number
    customer_code: string
    github_token: string
    organization: string
    token_type: string
    token_expires_at: string | null
    enabled: boolean
    auto_audit_enabled: boolean
    audit_schedule_cron: string | null
    include_repos: boolean
    include_workflows: boolean
    include_members: boolean
    include_archived_repos: boolean
    repo_filter_mode: string
    repo_filter_list: string[] | null
    notify_on_critical: boolean
    notify_on_high: boolean
    notification_webhook_url: string | null
    notification_email: string | null
    minimum_passing_score: number
    created_at: string
    updated_at: string
    created_by: string | null
    updated_by: string | null
    last_audit_at: string | null
    last_audit_score: number | null
    last_audit_grade: string | null
}

export interface GitHubAuditReportSummary {
    id: number
    config_id: number
    customer_code: string
    report_name: string
    organization: string
    audit_started_at: string
    audit_completed_at: string | null
    audit_duration_seconds: number | null
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
    status: string
    triggered_by: string
    triggered_by_user: string | null
}

export interface GitHubAuditReport extends GitHubAuditReportSummary {
    full_report: GitHubAuditResponse | null
    top_findings: AuditCheck[] | null
    error_message: string | null
}

export interface GitHubAuditCheckExclusion {
    id: number
    config_id: number
    customer_code: string
    check_id: string
    resource_name: string | null
    resource_type: string | null
    reason: string
    approved_by: string | null
    approved_at: string | null
    expires_at: string | null
    enabled: boolean
    created_at: string
    created_by: string
}

export interface GitHubAuditBaseline {
    id: number
    config_id: number
    customer_code: string
    name: string
    description: string | null
    expected_checks: Record<string, string> | null
    baseline_report_id: number | null
    is_active: boolean
    created_at: string
    created_by: string
}

export interface AvailableCheck {
    id: string
    name: string
    category: string
    severity: string
    description: string
}

// ==================== Audit Result Types ====================

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

// ==================== Response Types ====================

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

export interface GitHubAuditConfigResponse {
    success: boolean
    message: string
    config?: GitHubAuditConfig | null
    configs?: GitHubAuditConfig[] | null
}

export interface GitHubAuditReportListResponse {
    success: boolean
    message: string
    reports: GitHubAuditReportSummary[]
    total_count: number
}

export interface GitHubAuditReportResponse {
    success: boolean
    message: string
    report: GitHubAuditReport | null
}

export interface GitHubAuditExclusionResponse {
    success: boolean
    message: string
    exclusion?: GitHubAuditCheckExclusion | null
    exclusions?: GitHubAuditCheckExclusion[] | null
}

export interface GitHubAuditBaselineResponse {
    success: boolean
    message: string
    baseline?: GitHubAuditBaseline | null
    baselines?: GitHubAuditBaseline[] | null
}

export interface AvailableChecksResponse {
    success: boolean
    message: string
    checks: AvailableCheck[]
}

export interface DeleteResponse {
    success: boolean
    message: string
}
