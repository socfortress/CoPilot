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
	/** detections/<folder> the rule lives in, verbatim from the rules repo */
	category: string
	/** Display label for `category`, e.g. "EID 01 Process Creation" */
	category_label: string
	mitre_attack_id: string[]
	analytic_story: string[]
	cve: string[]
	file_path: string
	has_graylog_query: boolean
	/** "catalog" = shared SOCFortress repo, "custom" = a client's own repo */
	provenance?: "catalog" | "custom"
	owner_customer_code?: string | null
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
	provenance?: "catalog" | "custom"
	owner_customer_code?: string | null
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
	category: string | null
	rules: RuleSummary[]
}

/** One detections/ folder from the CoPilot-Search-Queries repo */
export interface RuleCategory {
	value: string
	label: string
	group: string
	count: number
}

export interface RuleCategoriesResponse {
	categories: RuleCategory[]
}

export interface RuleDetailResponse {
	rule: RuleDetail
}

export interface RuleStatsResponse {
	total_rules: number
	by_platform: Record<string, number>
	by_category: Record<string, number>
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
	category?: string
	status?: RuleStatus
	severity?: RuleSeverity
	mitre_id?: string
	search?: string
	has_graylog?: boolean
	provenance?: "catalog" | "custom"
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
	category?: string
}

export interface MitreCoverageQuery {
	platform?: PlatformFilter
	category?: string
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

// --- Detection rule editor: L1 validation (see DETECTION_RULE_EDITOR.md) ---
export interface LintFinding {
	level: "error" | "warning"
	code: string
	message: string
	path?: string
	line?: number | null
}

export interface ValidateRuleRequest {
	yaml: string
}

export interface ValidateRuleResponse {
	valid: boolean
	error_count: number
	warning_count: number
	findings: LintFinding[]
}

// --- Detection rule editor: backtest (see DETECTION_RULE_EDITOR.md) ---
export interface BacktestRequest {
	yaml: string
	customer_code: string
	range_seconds?: number
}

export interface BacktestBucket {
	bucket: string
	count: number
}

export interface BacktestTopValue {
	value: string
	count: number
}

export interface BacktestOffender {
	group: string
	windows_alerting: number
	peak: number
}

export interface BacktestSensitivity {
	threshold: number
	alerts: number
}

export interface BacktestAggregation {
	window: string
	window_seconds: number
	function: string
	field?: string | null
	group_by: string[]
	threshold: number
	condition: string
	estimated_alerts: number
	per_day_alerts: number
	top_offenders: BacktestOffender[]
	sensitivity: BacktestSensitivity[]
	truncated: boolean
}

export interface BacktestResponse {
	success: boolean
	message?: string
	error?: string | null
	mode?: "messages" | "aggregation" | null
	customer_code?: string | null
	stream_id?: string | null
	range_seconds?: number | null
	query?: string | null
	total_hits: number
	per_day_avg: number
	fetched: number
	truncated: boolean
	per_bucket: BacktestBucket[]
	bucket_unit?: string | null
	samples: Record<string, unknown>[]
	sample_fields: string[]
	top_fields: Record<string, BacktestTopValue[]>
	aggregation?: BacktestAggregation | null
	/** Query fields that don't exist in this customer's stream data (L4-lite) */
	missing_fields?: string[]
	note?: string | null
}

// --- Per-tenant custom rule repositories (see DETECTION_RULE_EDITOR.md) ---
export interface CustomRepoConfig {
	customer_code: string
	repo: string
	branch: string
	enabled: boolean
	has_token: boolean
	/** Fetch outcome from the last cache refresh (null = not refreshed yet this run) */
	last_refresh_ok?: boolean | null
	rules_loaded?: number | null
	last_refresh_error?: string | null
	last_refresh_at?: string | null
}

export interface TestCustomRepoRequest {
	repo: string
	branch?: string
	token?: string | null
	customer_code?: string | null
}

export interface TestCustomRepoResponse {
	ok: boolean
	rules_found: number
	error?: string | null
}

export interface SetCustomRepoRequest {
	repo: string
	branch?: string
	token?: string | null
	enabled?: boolean
}

export interface CustomRepoResponse {
	repo: CustomRepoConfig | null
}

export interface CustomRepoListResponse {
	repos: CustomRepoConfig[]
}

// --- Publish a rule to a client's own GitHub repo ---
export interface PublishRuleRequest {
	yaml: string
	customer_code: string
	message?: string
	path?: string
}

export interface PublishRuleResponse {
	success: boolean
	message?: string
	error?: string | null
	action?: "created" | "updated" | null
	repo?: string | null
	branch?: string | null
	path?: string | null
	commit_url?: string | null
	html_url?: string | null
	findings?: LintFinding[]
}
