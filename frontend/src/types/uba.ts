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

export interface UbaEntityDetail {
	tenant: string
	entity_key: string
	entity_type: string | null
	entity_name: string | null
	risk: number
	risk_by_rule: UbaRiskPart[]
	identity: UbaIdentity | null
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
