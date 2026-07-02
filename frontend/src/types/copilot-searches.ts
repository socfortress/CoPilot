export type PlatformFilter = "all" | "linux" | "windows" | "powershell" | "cve" | "cloud" | "office365" | "web"
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

export interface GraylogQuery {
	query: string
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
	has_graylog_query: boolean
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
	graylog: GraylogQuery | null
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
	total: number
	filtered: number
	platform: string
	rules: RuleSummary[]
}

export interface RuleDetailResponse {
	rule: RuleDetail
}

export interface RuleStatsResponse {
	total_rules: number
	by_platform: Record<string, number>
	by_status: Record<string, number>
	by_severity: Record<string, number>
	by_mitre_tactic: Record<string, number>
	rules_with_graylog: number
	last_refreshed: string | null
	cache_ttl_minutes: number
}

export interface RefreshResponse {
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
	rule_id: string
	rule_name: string
	total_hits: number
	returned_hits: number
	took_ms: number
	hits: SearchHit[]
	query_executed: Record<string, unknown>
}

// Graylog Query Types

export interface ExecuteGraylogQueryRequest {
	rule_id: string
	parameters?: Record<string, string | number | boolean>
}

export interface GraylogQueryResponse {
	rule_id: string
	rule_name: string
	graylog_query: string
	original_query: string
}

// Graylog Alert Provisioning Types

export interface ProvisionGraylogAlertRequest {
	rule_id: string
	search_within_seconds?: number
	execute_every_seconds?: number
	streams?: string[]
	custom_title?: string
	priority?: 1 | 2 | 3
	event_limit?: number
}

export interface ProvisionGraylogAlertResponse {
	rule_id: string
	rule_name: string
	alert_title: string
	graylog_query: string
}

export interface BulkProvisionGraylogAlertRequest {
	rule_ids: string[]
	search_within_seconds?: number
	execute_every_seconds?: number
	streams?: string[]
	priority?: 1 | 2 | 3
	event_limit?: number
}

export type BulkProvisionRuleStatus = "provisioned" | "skipped" | "failed"

export interface BulkProvisionRuleResult {
	rule_id: string
	rule_name: string | null
	alert_title: string | null
	status: BulkProvisionRuleStatus
	reason: string | null
}

export interface BulkProvisionGraylogAlertResponse {
	provisioned_count: number
	skipped_count: number
	failed_count: number
	results: BulkProvisionRuleResult[]
}

export interface GraylogProvisioningStatusResponse {
	provisioned: Record<string, boolean>
	warning: string | null
}

// Query Parameters

export interface RuleListQuery {
	platform?: PlatformFilter
	status?: RuleStatus
	severity?: RuleSeverity
	mitre_id?: string
	search?: string
	has_graylog?: boolean
	skip?: number
	limit?: number
}

// MITRE Coverage

export interface MitreSubTechnique {
	id: string
	name: string
	url: string
	rule_count: number
	rule_ids: string[]
}

export interface MitreTechnique {
	id: string
	name: string
	url: string
	rule_count: number
	rule_ids: string[]
	total_rule_count: number
	subtechniques: MitreSubTechnique[]
}

export interface MitreTactic {
	id: string
	name: string
	short_name: string
	url: string
	techniques: MitreTechnique[]
}

export interface MitreCoverageStats {
	total_tactics: number
	total_techniques: number
	covered_techniques: number
	total_rules: number
	matrix_last_refreshed: string | null
	rules_last_refreshed: string | null
}

export interface MitreRuleIndexEntry {
	id: string
	name: string
	severity: string
	platform: string
	has_graylog: boolean
	data_sources: string[]
}

export interface RulesByMitreQuery {
	techniqueId: string
	platform?: PlatformFilter
}

export interface MitreCoverageQuery {
	platform?: PlatformFilter
	severity?: RuleSeverity
	status?: RuleStatus
	has_graylog?: boolean
	search?: string
}

export interface MitreCoverageResponse {
	tactics: MitreTactic[]
	rules_index: Record<string, MitreRuleIndexEntry>
	stats: MitreCoverageStats
}

// Batch rule lookup

export interface RulesByIdsRequest {
	ids: string[]
}

export interface RulesByIdsResponse {
	rules: RuleSummary[]
	missing: string[]
}
