/**
 * `GET /api/talon/health` (the Talon health dashboard): CoPilot's own checks of its Talon connector,
 * plus talon-analyst's `/v2/health`, `/v2/health/history` and `/v2/health/metrics` as CoPilot relays
 * them (`backend/app/connectors/talon/schema/talon_health.py`).
 *
 * CoPilot copies talon-analyst's fields one by one and bounds them, but the UI still treats every
 * field as possibly missing: a newer or older talon-analyst may send less.
 */

export type TalonComponentStatus = "ok" | "warn" | "fail" | "off" | "unknown"
export type TalonOverallStatus = "ok" | "degraded" | "down" | "unknown"
export type TalonComponentGroup = "core" | "mcp" | "model" | "other"
export type TalonSwitch = boolean | string | null

export interface TalonProbe {
	ok: boolean | null
	latency_ms: number | null
	status_code: number | null
	error: string | null
}

export interface TalonJobSummary {
	customer_code: string
	status: string | null
	/** Naive UTC. */
	at: string
}

export interface TalonCopilotView {
	connector: { exists: boolean; configured: boolean; verified: boolean; url: string | null }
	reachable: TalonProbe
	auth: TalonProbe
	v2_enabled: boolean
	last_sent: TalonJobSummary | null
	last_job: TalonJobSummary | null
	last_report: TalonJobSummary | null
	jobs_failed_24h: number
	ai_trigger_customers: number
	scope: "deployment" | "assigned"
}

export interface TalonHealthComponent {
	id: string
	name: string
	group: TalonComponentGroup
	status: TalonComponentStatus
	latency_ms: number | null
	detail: string | null
	fix: string | null
	checked_at: string | null
}

export interface TalonHealthConfig {
	writeback_mode: string | null
	live_customers: string[]
	automation_max_level: number | null
	automation_policy_source: string | null
	v2_api: TalonSwitch
	action_tools: TalonSwitch
	endpoint_actions: TalonSwitch
	intel: TalonSwitch
	workspace_tools: TalonSwitch
	chat_browser: TalonSwitch
	models: { chat: string | null; investigation: string | null }
	/**
	 * Decimal strings. A ceiling is "unlimited" when talon-analyst reported none, null when it wasn't
	 * reported; `budgets` itself is null when talon-analyst sent none.
	 */
	budgets: {
		daily_usd: string | null
		monthly_usd: string | null
		spent_today_usd: string | null
		spent_month_usd: string | null
	} | null
}

export interface TalonHealthData {
	status: TalonOverallStatus
	version: string | null
	image_browser: boolean | null
	uptime_seconds: number | null
	checked_at: string | null
	components: TalonHealthComponent[]
	config: TalonHealthConfig | null
}

export interface TalonHistoryBucket {
	t: string
	ok: number | null
	warn: number | null
	fail: number | null
}

export interface TalonHistoryData {
	bucket_minutes: number | null
	components: Record<string, TalonHistoryBucket[]>
}

/** `null` is "no data source": shown as "no data", never 0. */
export interface TalonMetricsBucket {
	t: string
	investigations_completed: number | null
	investigations_failed: number | null
	queue_depth_max: number | null
	duration_p50_s: number | null
	duration_p95_s: number | null
	tool_calls: number | null
	tool_errors: number | null
	model_errors: number | null
	/** A decimal string. */
	cost_usd: string | null
}

export interface TalonMetricsData {
	bucket_minutes: number | null
	series: TalonMetricsBucket[]
}

export interface TalonSection<T> {
	data: T | null
	error: string | null
	status_code: number | null
	/** A Talon older than the health API (it answered 404). */
	unsupported: boolean
}

export interface TalonHealthReport {
	success: boolean
	message: string
	hours: number
	/** When CoPilot asked Talon (UTC); up to 30 s old, CoPilot's cache. */
	checked_at: string
	copilot: TalonCopilotView
	health: TalonSection<TalonHealthData>
	history: TalonSection<TalonHistoryData>
	metrics: TalonSection<TalonMetricsData>
}
