export interface ConfigContent {
	customer_code: string
	config_content: string
}

export interface UploadConfigFileResponse {
	customer_code: string
	filename: string
	overwritten: boolean
}

export interface DeployConfigResponse {
	customer_code: string
	worker_success: boolean
	worker_message: string
	error_detail: string
	/** The Sysmon health apply run after an admin's deploy (it adds the sysmon-reload wodle). */
	sysmon_health?: { success: boolean; message: string } | null
	/** Set when the endpoints will not apply the deployed config yet, and why. */
	sysmon_health_warning?: string | null
}

/** This CoPilot's default Sysmon config, which pre-fills "Add new Configuration". */
export interface DefaultConfigResponse {
	/** Whether a default is set on this CoPilot. */
	present: boolean
	/** The default, rendered for `rendered_for` when a customer code was given. */
	config_content: string | null
	/**
	 * The customer code that replaced each __INSTALLDIRNAME__ placeholder. Null when no customer code was given, or when
	 * the default has no placeholder: then it comes back as stored.
	 */
	rendered_for: string | null
	/** How many times __INSTALLDIRNAME__ occurs in the stored default. Each was replaced when `rendered_for` is set. */
	placeholders: number
}

export interface SaveDefaultConfigResponse {
	/** How many times __INSTALLDIRNAME__ occurs in what was saved. */
	placeholders: number
	/** How many of the customer's install-folder paths were turned back into the placeholder. */
	restored: number
}

/** SYSMON_DEFAULT_SYNC: "on" applies a SOCFortress release unless the default was changed here, "force" always does. */
export type DefaultSyncMode = "on" | "force" | "off"

export type DefaultSyncOutcome =
	| "applied"
	| "adopted"
	| "up_to_date"
	| "local_default_differs"
	| "off"
	| "not_configured"
	| "invalid_url"
	| "no_license"
	| "unauthorized"
	| "license_rejected"
	| "not_published"
	| "rate_limited"
	| "service_unavailable"
	| "http_error"
	| "redirect_refused"
	| "too_large"
	| "network_error"
	| "verification_failed"
	| "invalid_config"
	| "rollback_refused"
	| "store_error"
	| "error"

/** One check of the SOCFortress default sync. */
export interface DefaultSyncCheck {
	outcome: DefaultSyncOutcome
	/** Whether the default is SOCFortress's latest release after this check (applied, adopted or up to date). */
	ok: boolean
	message: string
	mode: DefaultSyncMode
	forced: boolean
	/** UTC, YYYY-MM-DDTHH:MM:SSZ */
	checked_at: string
	/** The release the check got from the service, when it got one. */
	sequence: number | null
	commit: string | null
}

/** The SOCFortress release this CoPilot's default was last synced to. */
export interface DefaultSyncApplied {
	sequence: number
	commit: string
	content_sha256: string
	content_sha256_crlf: string | null
	key_id: string | null
	applied_at: string | null
	created_at: string | null
	schemaversion: string | null
	source: string | null
	service_url: string | null
}

export interface DefaultSyncStatus {
	mode: DefaultSyncMode
	/** SYSMON_DEFAULT_SYNC as set, when it is not one of on / force / off (sync then runs as "on"). */
	mode_setting: string | null
	service_url: string
	/** Whether this CoPilot version ships a trusted SOCFortress release key. */
	configured: boolean
	trusted_key_ids: string[]
	last_check: DefaultSyncCheck | null
	applied: DefaultSyncApplied | null
	default_present: boolean | null
	/** The stored default was changed here since the release in `applied`: sync leaves it alone. */
	local_default_differs: boolean | null
	read_error: string | null
}

export interface DefaultSyncStatusResponse {
	status: DefaultSyncStatus
}

export interface DefaultSyncRunResponse {
	result: DefaultSyncCheck
	status: DefaultSyncStatus
}

/** SYSMON_STATS_SHARING: "on" sends each customer's weekly noise report (unless opted out), "off" sends nothing. */
export type StatsMode = "on" | "off"

export type StatsOutcome =
	| "sent"
	| "withdrawn"
	| "refused"
	| "local_refused"
	| "refused_bad_request"
	| "refused_content_type"
	| "too_large"
	| "week_not_accepted"
	| "week_before_first_seen"
	| "customer_limit"
	| "storage_quota"
	| "waf_refused"
	| "no_sysmon_events"
	| "ambiguous_label"
	| "unauthorized"
	| "license_rejected"
	| "license_blocked"
	| "service_not_accepting"
	| "http_error"
	| "redirect_refused"
	| "body_timeout"
	| "busy"
	| "rate_limited"
	| "service_unavailable"
	| "storage_full"
	| "network_error"
	| "indexer_error"
	| "indexer_timeout"
	| "store_error"
	| "error"
	| "sharing_off"
	| "nothing_due"
	| "latched"
	| "no_license"
	| "invalid_url"
	| "indexer_fields_unavailable"
	| "indexer_unreachable"
	| "locked"
	| "running"
	| "completed"
	/** Send now: the run goes on in the background; the status shows its result. */
	| "started"

/** One customer's report of one ISO week: counts and hashes only, never a value. */
export interface StatsWeekState {
	/** "terminal": done for the week; "pending": a later run tries again. */
	status: "terminal" | "pending"
	outcome: StatsOutcome
	message: string | null
	attempts: number
	last_attempt_at: string | null
	not_before: string | null
	http_status: number | null
	reason: string | null
	sent_at: string | null
	payload_sha256: string | null
	payload_bytes: number | null
	patterns: number | null
	truncated: boolean | null
	endpoints: number | null
	config: number | string | null
	accepted: number | null
	rejected: number | null
	rejected_by_reason: Record<string, number>
	replaced: boolean | null
	local_drops: Record<string, number>
	/** Event IDs left out because a key field is not aggregatable in the indexer (the report is truncated). */
	unavailable_events?: number[]
}

export interface StatsService {
	/** Whether SOCFortress accepts reports; null while not known yet. */
	accepting: boolean | null
	/** Whether the last probe got an answer; null while not known yet. */
	reachable?: boolean | null
	checked_at: string | null
	last_status: number | null
	not_before: string | null
}

export interface StatsLastTick {
	started_at: string | null
	finished_at: string | null
	outcome: StatsOutcome | null
	message: string | null
	sent: number
	pending: number
	terminal: number
	week: string | null
}

/** Reports are paused: SOCFortress refused one for its content. */
export interface StatsLatch {
	set_at: string
	reason: string
	copilot_version: string
}

export interface StatsCustomer {
	customer_code: string
	customer_name: string | null
	/** The customer's id in this CoPilot's reports (cust_ + 32 hex). */
	pseudonym: string | null
	sharing: boolean
	install_dir_name: string | null
	own_domains: string[]
	withdraw: { queued: boolean; requested_at: string | null; withdrawn_at: string | null; last_status: number | null }
	/** When the target week's report is sent (UTC). */
	due_at: string | null
	target_week_state: StatsWeekState | null
	last_sent_week: string | null
	last_sent_state: StatsWeekState | null
}

export interface StatsStatus {
	mode: StatsMode
	/** SYSMON_STATS_SHARING as set, when CoPilot does not know it (then: off). */
	mode_setting: string | null
	service_url: string
	service: StatsService
	last_tick: StatsLastTick | null
	latch: StatsLatch | null
	target_week: string
	max_rule_level: number
	min_endpoints: number
	customers: StatsCustomer[]
	read_error: string | null
	/** A run (a tick or Send now) or a preview is in progress. */
	running?: boolean
}

export interface StatsStatusResponse {
	status: StatsStatus
}

export interface StatsSharingBody {
	sharing: boolean
	install_dir_name?: string | null
	own_domains?: string[] | null
}

export interface StatsSharingResponse {
	customer: StatsCustomer
	withdraw: { outcome: "withdrawn" | "queued" | "failed"; reports_deleted: number | null; message: string | null } | null
}

export interface StatsPreview {
	week: string
	customer_pseudonym: string
	would_send: { ok: boolean; why: string | null }
	/** The exact report whose compact UTF-8 JSON would be sent. */
	payload: Record<string, unknown> | null
	payload_sha256: string | null
	payload_bytes: number | null
	local: {
		raw_patterns: number
		sent: number
		dropped_by_reason: Record<string, number>
		merged: number
		truncated: boolean
		unavailable_events?: number[]
	}
	outcome: StatsOutcome | null
	message: string | null
	ms: number
}

export interface StatsPreviewResponse {
	preview: StatsPreview
}

export interface StatsRunResult {
	outcome: StatsOutcome
	message: string
	week: string | null
	customers: { customer_code: string; outcome: StatsOutcome; message: string | null }[]
}

export interface StatsRunResponse {
	result: StatsRunResult
	status: StatsStatus
}
