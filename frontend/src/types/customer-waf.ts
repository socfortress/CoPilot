// Mirrors backend/app/customer_waf/schema/customer_waf.py (#1165).
// The WAF's service token is write-only: no type here ever carries it back.

export interface CustomerWafInstance {
	id: number
	customer_code: string
	name: string
	api_url: string
	/** First characters of the token, e.g. "wafst_AbC12..." — the token itself is never returned. */
	token_prefix: string
	verify_tls: boolean
	has_ca_cert: boolean
	enabled: boolean
	last_verified_at: string | null
	/** Comma-joined WAF roles of the token's user at the last connection test. A hint, not authorisation. */
	last_verified_role: string | null
	created_by: number | null
	created_at: string | null
	updated_by: number | null
	updated_at: string | null
}

export interface CustomerWafPayload {
	name: string
	api_url: string
	/** Required on create. On update, blank keeps the stored token. */
	service_token?: string
	verify_tls: boolean
	ca_cert_pem?: string | null
	enabled: boolean
}

export interface CustomerWafCapabilities {
	can_read: boolean
	can_block: boolean
	can_manage_forwarders: boolean
}

/** Stable failure codes from the backend; see app/customer_waf/utils/universal.py. */
export type CustomerWafFailureReason =
	| "unreachable"
	| "tls_error"
	| "token_rejected"
	| "insufficient_role"
	| "not_a_waf"
	| "not_found"
	| "bad_response"
	| "upstream_error"
	| "disabled"
	| "token_crypto"
	| "invalid_target"
	| "blocked_by_waf_rule"
	| "not_blocked"

export interface CustomerWafVerification {
	reachable: boolean
	authenticated: boolean
	reason: CustomerWafFailureReason | null
	detail: string | null
	waf_user_email: string | null
	waf_roles: string[]
	capabilities: CustomerWafCapabilities
	health: { status?: string; db?: string; redis?: string } | null
}

export interface CustomerWafSite {
	id: string
	name: string
	hostname: string
	upstream_url: string
	is_enabled: boolean
	detection_mode: boolean
	created_at: string | null
}

export type CustomerWafAction = "blocked" | "detected" | "passed"

export interface CustomerWafEvent {
	id: string
	timestamp: string
	transaction_id: string
	site_id: string | null
	client_ip: string
	method: string
	uri: string
	host: string
	rule_id: string | null
	action: CustomerWafAction | string
	severity: string | null
	anomaly_score: number | null
	matched_rules: { id: string | null; msg: string | null }[]
	geoip_country_code: string | null
	geoip_country_name: string | null
	geoip_city: string | null
}

export interface CustomerWafEventsQuery {
	action?: CustomerWafAction | null
	severity?: string | null
	client_ip?: string | null
	rule_id?: string | null
	site_id?: string | null
	start_time?: string | null
	end_time?: string | null
	limit?: number
	offset?: number
}

export interface CustomerWafStats {
	total_1h: number
	blocked_1h: number
	detected_1h: number
	block_rate: number
	top_rules: { rule_id: string | null; count: number }[]
	top_ips: { client_ip: string; count: number }[]
	requests_per_hour: { hour: string; count: number }[]
	attack_categories: { category: string; count: number }[]
	top_countries: { country_code: string | null; country_name: string | null; count: number }[]
	ingestion_lag_seconds: number | null
	events_per_minute: number | null
	caddy_healthy: boolean | null
}

export interface CustomerWafThreatIntelEntry {
	ip_address: string
	block_count: number
	rule_hit_count: number
	total_events: number
	threat_score: number
	top_rules: { rule_id: string | null; count: number }[]
	country_code: string | null
	country_name: string | null
	first_seen_at: string
	last_seen_at: string
	is_blocked: boolean
}

export interface CustomerWafThreatIntelSummary {
	total_ips: number
	last_run_at: string | null
	window_days: number | null
	min_score: number | null
}

export interface CustomerWafBlock {
	target: string
	rule_uuid: string
	rule_id: number
	name: string
	description: string
	enabled: boolean
	created_by_copilot: boolean
	created_at: string | null
}

export type CustomerWafBlockAction = "created" | "reenabled" | "already_blocked" | "blocked_by_waf_rule"

export interface CustomerWafBlockPayload {
	target: string
	reason: string
	alert_id?: number | null
	case_id?: number | null
}
