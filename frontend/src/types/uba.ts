// SOCFortress UBA (user behavior analytics), proxied by /api/uba. Shapes mirror UBA's /v1 API
// (socfortress-uba docs/12-api.md). Upstream failures come back as 502/404/409/422 with a `reason`.

export type UbaFailureReason = "not_configured" | "unreachable" | "key_rejected" | "insufficient_scope" | "not_found" | "invalid_request" | "upstream_error" | "bad_response"

export interface UbaAvailability {
	configured: boolean
	verified: boolean
}

export interface UbaTenantStatus {
	tenant: string
	processed_until: string | null
	lag_seconds: number | null
	bootstrapped_until?: string | null
	alerts_24h: number
	open_alerts: number
	signals_24h: number
	/** Health of each source feeding UBA (absent from UBA versions before feed health). */
	feeds?: UbaFeedStatus[]
	/** Onboarding state (absent from UBA versions before tenant registration). */
	onboarding?: UbaOnboardingStatus | null
	/** The customer's computers with a Wazuh agent (UBA 1.3+). */
	agents?: UbaAgentsSummary | null
}

export type UbaOnboardingStatus = "inactive" | "pending" | "bootstrapping" | "error" | "live"

/** UBA's registration of a customer and its history replay (GET /v1/tenants/{code}/onboarding). */
export interface UbaOnboarding {
	tenant: string
	name: string
	status: UbaOnboardingStatus
	active: boolean
	bootstrap_days: number
	bootstrap_since: string | null
	/** History replayed up to here. */
	bootstrap_cursor: string | null
	bootstrap_docs: number
	bootstrap_error: string | null
	bootstrapped_until: string | null
	office365_organization_ids: string[]
	indices: Record<string, string>
}

export interface UbaProvisioning {
	/** Source streams UBA would read, per source (WAZUH, O365). */
	sources: Record<string, number>
	office365_tenants: string[]
	/** Why UBA cannot be set up yet (e.g. the customer is not provisioned). */
	problem: string | null
	/** Null when UBA does not know the customer. */
	onboarding: UbaOnboarding | null
}

export interface UbaProvisionPayload {
	bootstrap_days: number
	deploy_wazuh_rules: boolean
}

export interface UbaProvisionStep {
	step: string
	status: string
	detail: string
}

export type UbaFeedState = "ok" | "lagging" | "quiet" | "repeating"

export interface UbaFeedStatus {
	source: string
	status: UbaFeedState
	/** Every problem found, in words. */
	reasons: string[]
	newest_event: string | null
	last_received: string | null
	/** Median age of the events received in the last 15 minutes. */
	lag_p50_s: number | null
	received_1h: number
	/** Records the source sent again (already processed). */
	repeated_1h: number
	updated_at: string | null
}

export interface UbaPage {
	total: number
	page: number
	page_size: number
}

export interface UbaEntitySummary {
	entity_key: string
	entity_type: string | null
	entity_name: string | null
	risk: number
	last_signal: string | null
	signals_24h: number
	rules: number
	open_alert_id: string | null
}

export interface UbaAlias {
	type: string
	value: string
	source: string | null
	confidence: number | null
	last_seen: string | null
}

export interface UbaIdentity {
	id: string
	kind: string | null
	display_name: string | null
	privileged: boolean
	privileged_reasons: string[]
	shadow: boolean
	tags: string[]
	/** When UBA first saw the identity. */
	created_at: string | null
	/** Account state in the directory, when known (Entra/AD sync or account-change events). */
	enabled?: boolean | null
	account_created_at?: string | null
	deleted_at?: string | null
	/** Which source set an attribute, e.g. `{ enabled: "entra_audit" }`. */
	attr_source?: Record<string, string>
	aliases: UbaAlias[]
	memberships?: UbaMembership[]
}

export interface UbaMembership {
	group_name: string
	group_id: string | null
	/** entra (directory sync), entra_audit / windows_audit (account-change events), manual, ... */
	source: string
	privileged: boolean
	/** When the membership was granted (event time), if known. */
	since: string | null
}

export type UbaIdentitySourceStatus = "new" | "ok" | "error" | "queued" | "disabled"

export interface UbaIdentitySource {
	id: string
	type: string
	status: UbaIdentitySourceStatus
	entra_tenant_id: string | null
	client_id: string | null
	every_s: number | null
	last_sync: string | null
	last_error: string | null
	last_result: Record<string, number | boolean | string[]>
}

export interface UbaRiskPart {
	rule_id: string
	signals: number
	risk: number
	last_signal: string | null
	native: boolean
}

export interface UbaSignal {
	id: string
	rule_id: string
	entity_type: string | null
	entity_key: string
	entity_name: string | null
	time: string
	score: number
	effective_score: number
	explanation: string
	event_class: string | null
	mitre: string[]
	evidence: string[]
	native: boolean
	suppressed: boolean
}

export interface UbaSuppression {
	tenant_id: string
	entity_key: string
	rule_id: string
	until: string
	reason: string | null
	source: string | null
	created_at: string | null
	active: boolean
}

export interface UbaAlert {
	id: string
	tenant_id: string
	entity_key: string
	entity_type: string | null
	entity_name: string | null
	opened_at: string
	risk: number
	reason: string | null
	rules: string[]
	update_count: number
	last_update_at: string | null
	verdict: "TRUE_POSITIVE" | "FALSE_POSITIVE" | string | null
	verdict_reason: string | null
	verdict_note: string | null
	verdict_by: string | null
	verdict_at: string | null
	copilot_alert_id: number | null
}

export interface UbaAlertUpdate {
	time: string
	rule_id: string | null
	effective?: number
	risk?: number
	explanation: string | null
}

export type UbaReportingState = "reporting" | "not_reporting" | "retired" | "never_connected"

/** A computer with a Wazuh agent (UBA reads the Wazuh dashboard's agent snapshots). */
export interface UbaHost {
	agent_id: string
	name: string
	os: string | null
	platform: string | null
	/** server or workstation (Windows, by edition). */
	role: string | null
	ip: string | null
	/** Wazuh's agent status: active, disconnected, ... */
	status: string | null
	reporting: UbaReportingState
	last_keepalive: string | null
	agent_version: string | null
	groups: string[]
	registered_at: string | null
	updated_at: string | null
}

export interface UbaAgentsSummary {
	total: number
	reporting: number
	not_reporting: number
	retired: number
	never_connected: number
	/** The computers not reporting (at most 20). */
	not_reporting_hosts: UbaHost[]
	updated_at: string | null
}

export interface UbaEntityDetail {
	tenant: string
	entity_key: string
	entity_type: string | null
	entity_name: string | null
	risk: number
	risk_by_rule: UbaRiskPart[]
	identity: UbaIdentity | null
	/** The computer, when the entity is a Wazuh agent (UBA 1.3+). */
	host?: UbaHost | null
	alerts: UbaAlert[]
	suppressions: UbaSuppression[]
}

export interface UbaRuleStat {
	rule_id: string
	signals: number
	entities: number
	with_risk: number
	suppressed: number
	native: boolean
	last_signal: string | null
}

export interface UbaEntitiesQuery {
	entity_type?: string | null
	q?: string | null
	min_risk?: number
	native?: boolean
	page?: number
	page_size?: number
}

export interface UbaFeedbackPayload {
	verdict: "TRUE_POSITIVE" | "FALSE_POSITIVE"
	reason?: string | null
	note?: string | null
	suppress?: boolean
	suppress_days?: number
}

export interface UbaSuppressionPayload {
	entity_key: string
	rule_ids: string[]
	days?: number
	reason?: string | null
}

export interface UbaEvidenceEvent {
	gl2_message_id: string
	index: string
	id: string
	/** Graylog receive time. */
	timestamp: string | null
	/** The indexed document; values over 4,000 characters are clipped by UBA. */
	source: Record<string, unknown>
}

export interface UbaEvidence {
	signal_id: string
	rule_id: string
	events: UbaEvidenceEvent[]
	/** Ids no longer in the indexer (index retention). */
	missing: string[]
	note: string | null
}

export type UbaRiskStep = "15m" | "1h" | "6h" | "1d"

export interface UbaRiskHistory {
	entity_key: string
	step: UbaRiskStep
	alert_threshold: number
	/** Risk at each step (UBA's current-risk formula applied at that time); the last point is now. */
	points: { time: string; risk: number; native: number }[]
	/** Contributions in the window (the 200 largest), by time. */
	findings: { id: string; time: string; rule_id: string; effective_score: number; native: boolean; explanation: string | null }[]
	alerts: { id: string; opened_at: string; risk: number }[]
}

/** One UBA rule from its catalog (the fields the UI uses). */
export interface UbaRuleInfo {
	id: string
	name: string
	enabled?: boolean
	score?: number
	mitre?: string[]
	detector?: { type: string }
}

export type UbaBacktestStatus = "queued" | "running" | "cancelling" | "done" | "error" | "cancelled"

export interface UbaBacktestPayload {
	days: number
	warmup_days: number
	rules?: string[]
	filter?: string
}

export interface UbaBacktestRuleResult {
	rule_id: string
	signals: number
	per_day: number
	entities: number
	top_entities: { entity: string; signals: number }[]
	days: Record<string, number>
	samples: string[]
}

export interface UbaBacktestResult {
	since: string
	until: string
	docs: number
	warmup_docs: number
	/** Stopped at UBA's document limit: covers only part of the window. */
	truncated: boolean
	rules: UbaBacktestRuleResult[]
	native_contributions: number
	alerts: { entity: string; rules: string[]; risk: number; reason: string | null }[]
	alert_count: number
	alert_updates: number
}

export interface UbaBacktest {
	id: string
	status: UbaBacktestStatus
	params: UbaBacktestPayload
	requested_by: string | null
	created_at: string
	started_at: string | null
	finished_at: string | null
	progress: { docs?: number; phase?: string }
	error: string | null
	result: UbaBacktestResult | null
}

/** UBA's risk policy, in the numbers the About card explains. */
export interface UbaRiskPolicy {
	alert_threshold: number
	/** One finding at least this strong (after weighting) alerts on its own. */
	single_signal_threshold: number
	half_life_hours: number
	horizon_days: number
	repeat_window_hours: number
	repeat_decay: number
	privileged_multiplier: number
	/** Native (Wazuh) alerts add at most this much per entity per repeat window. */
	max_native_per_window: number
}

export interface UbaAboutRule {
	id: string
	name: string
	/** What it detects and why it matters, in plain words. */
	description: string
	/** How it decides, written from the rule's settings. */
	how: string
	score: number
	/** Whose risk it adds to, in words ("the person or program that acted", "the computer", ...). */
	about: string
	mitre: string[]
	enabled: boolean
}

export interface UbaAbout {
	policy: UbaRiskPolicy
	rule_count: number
	categories: { id: string; label: string; summary: string; rules: UbaAboutRule[] }[]
}

/** One UBA rule as it applies to a customer (GET /v1/tenants/{code}/rule-settings). */
export interface UbaRuleSetting {
	rule_id: string
	name: string
	/** Rule id prefix: auth, account, mail, saas, file, process, inventory. */
	category: string
	default_enabled: boolean
	default_score: number
	enabled: boolean
	score: number
	/** The customer has its own setting for this rule. */
	customized: boolean
	changed_by: string | null
	changed_at: string | null
}

export interface UbaAlertThreshold {
	value: number
	default: number
	customized: boolean
	changed_by: string | null
	changed_at: string | null
	/** One finding worth this much alerts at once (not per customer). */
	single_finding: number
}

export interface UbaRuleSettings {
	rules: UbaRuleSetting[]
	alert_threshold: UbaAlertThreshold
}

/** Only the fields sent change; null puts one back to the built-in value. */
export interface UbaRuleSettingPayload {
	enabled?: boolean | null
	score?: number | null
}
