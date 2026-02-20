export type PlatformFilter = "all" | "linux" | "windows"
export type RuleStatus = "production" | "experimental" | "deprecated"
export type RuleSeverity = "low" | "medium" | "high" | "critical"

export interface ParameterSchema {
    name: string
    description: string
    type: string
    required: boolean
    default?: string | number | boolean | null
    example?: string | number | boolean | null
}

export interface RuleSummary {
    id: string
    name: string
    version: number
    status: string
    type: string
    description: string
    author: string
    date: string
    severity: string
    risk_score: number
    platform: string
    mitre_attack_id: string[]
    analytic_story: string[]
    cve: string[]
    file_path: string
}

export interface RuleDetail {
    id: string
    name: string
    version: number
    schema_version: string
    status: string
    type: string
    description: string
    author: string
    date: string
    data_source: string[]
    search: Record<string, unknown>
    parameters: ParameterSchema[]
    how_to_implement: string
    known_false_positives: string
    references: string[]
    response: RuleResponse
    tags: RuleTags
    file_path: string
    raw_yaml: string
}

export interface RuleResponse {
    message: string
    risk_score: number
    severity: string
    risk_objects: RiskObject[]
    threat_objects: ThreatObject[]
}

export interface RiskObject {
    field: string
    type: string
    score: number
}

export interface ThreatObject {
    field: string
    type: string
}

export interface RuleTags {
    analytic_story: string[]
    asset_type: string
    mitre_attack_id: string[]
    product: string[]
    security_domain: string
    cve?: string[]
}

export interface RuleListResponse {
    success: boolean
    message: string
    total: number
    filtered: number
    platform: string
    rules: RuleSummary[]
}

export interface RuleDetailResponse {
    success: boolean
    message: string
    rule: RuleDetail
}

export interface RuleStatsResponse {
    success: boolean
    message: string
    total_rules: number
    by_platform: Record<string, number>
    by_status: Record<string, number>
    by_severity: Record<string, number>
    by_mitre_tactic: Record<string, number>
    last_refreshed: string | null
    cache_ttl_minutes: number
}

export interface RefreshResponse {
    success: boolean
    message: string
    rules_loaded: number
    timestamp: string
}

// Search Execution Types

export interface ExecuteSearchRequest {
    rule_id: string
    index_pattern: string
    parameters: Record<string, string | number | boolean>
    size?: number
}

export interface SearchHit {
    index: string
    id: string
    score: number | null
    source: Record<string, unknown>
}

export interface ExecuteSearchResponse {
    success: boolean
    message: string
    rule_id: string
    rule_name: string
    total_hits: number
    returned_hits: number
    took_ms: number
    hits: SearchHit[]
    query_executed: Record<string, unknown>
}

export interface SearchValidationError {
    parameter: string
    message: string
}

export interface ExecuteSearchErrorResponse {
    success: boolean
    message: string
    rule_id?: string
    validation_errors: SearchValidationError[]
}

// Query Parameters

export interface RuleListQuery {
    platform?: PlatformFilter
    status?: RuleStatus
    severity?: RuleSeverity
    mitre_id?: string
    search?: string
    skip?: number
    limit?: number
}
