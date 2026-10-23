import type {
	TalonHealthComponent,
	TalonHealthConfig,
	TalonHealthReport,
	TalonMetricsBucket,
	TalonSection
} from "@/types/talonHealth"
import { OLD_TALON_TEXT } from "../health"

export function component(id: string, extra: Partial<TalonHealthComponent> = {}): TalonHealthComponent {
	return {
		id,
		name: id.replace(/_/g, " "),
		group: "core",
		status: "ok",
		latency_ms: 12,
		detail: `${id} fine`,
		fix: null,
		checked_at: "2026-10-22T08:00:00Z",
		...extra
	}
}

export function config(extra: Partial<TalonHealthConfig> = {}): TalonHealthConfig {
	return {
		writeback_mode: "live",
		live_customers: ["ACME", "GLOBEX"],
		automation_max_level: 1,
		automation_policy_source: "copilot",
		v2_api: true,
		action_tools: false,
		endpoint_actions: true,
		intel: true,
		workspace_tools: false,
		chat_browser: null,
		models: { chat: "claude-sonnet-5-5", investigation: "claude-opus-5-5" },
		budgets: { daily_usd: "25.00", monthly_usd: null, spent_today_usd: "20.00", spent_month_usd: "41.20" },
		...extra
	}
}

export function bucket(t: string, extra: Partial<TalonMetricsBucket> = {}): TalonMetricsBucket {
	return {
		t,
		investigations_completed: 4,
		investigations_failed: 1,
		queue_depth_max: 2,
		duration_p50_s: 61.5,
		duration_p95_s: 140,
		tool_calls: 50,
		tool_errors: null,
		model_errors: 0,
		cost_usd: "1.2345",
		...extra
	}
}

function section<T>(data: T | null, extra: Partial<TalonSection<T>> = {}): TalonSection<T> {
	return { data, error: null, status_code: data === null ? null : 200, unsupported: false, ...extra }
}

/** A section Talon couldn't fill. */
function empty(extra: Partial<TalonSection<never>>): TalonSection<never> {
	return { data: null, error: null, status_code: null, unsupported: false, ...extra }
}

/** A healthy talon-analyst 0.1.3, seen by an admin. */
export function healthReport(extra: Partial<TalonHealthReport> = {}): TalonHealthReport {
	return {
		success: true,
		message: "Talon health retrieved",
		hours: 24,
		checked_at: new Date(Date.now() - 12_000).toISOString(),
		copilot: {
			connector: { exists: true, configured: true, verified: true, url: "http://talon-analyst-api:3100" },
			reachable: { ok: true, latency_ms: 8.4, status_code: 200, error: null },
			auth: { ok: true, latency_ms: null, status_code: 200, error: null },
			v2_enabled: true,
			last_sent: { customer_code: "ACME", status: "pipeline", at: "2026-10-22T07:59:00" },
			last_job: { customer_code: "ACME", status: "completed", at: "2026-10-22T07:59:05" },
			last_report: { customer_code: "ACME", status: null, at: "2026-10-22T08:01:00" },
			jobs_failed_24h: 1,
			ai_trigger_customers: 2,
			scope: "deployment"
		},
		health: section({
			status: "degraded",
			version: "0.1.3",
			image_browser: false,
			uptime_seconds: 93_600,
			checked_at: "2026-10-22T08:00:00Z",
			components: [
				component("api"),
				component("database"),
				component("wazuh_mcp", { group: "mcp", status: "warn", fix: "Check the Wazuh API account" }),
				component("model_provider", { group: "model", status: "fail", detail: "429 from the provider" })
			],
			config: config()
		}),
		history: section({
			bucket_minutes: 60,
			components: {
				api: [{ t: "2026-10-22T07:00:00Z", ok: 12, warn: 0, fail: 0 }],
				wazuh_mcp: [{ t: "2026-10-22T07:00:00Z", ok: 10, warn: 2, fail: 0 }]
			}
		}),
		metrics: section({
			bucket_minutes: 60,
			series: [bucket("2026-10-22T07:00:00Z"), bucket("2026-10-22T08:00:00Z", { cost_usd: null })]
		}),
		...extra
	}
}

/** Talon could not be reached: CoPilot's own checks only. */
export function unreachableReport(): TalonHealthReport {
	const error = "Talon could not be reached (ConnectError)"
	return healthReport({
		copilot: {
			...healthReport().copilot,
			reachable: { ok: false, latency_ms: null, status_code: null, error },
			auth: { ok: null, latency_ms: null, status_code: null, error }
		},
		health: empty({ error }),
		history: empty({ error }),
		metrics: empty({ error })
	})
}

/** A Talon older than the health API: every section answered 404. */
export function oldTalonReport(): TalonHealthReport {
	const old = { error: OLD_TALON_TEXT, status_code: 404, unsupported: true }
	return healthReport({
		health: empty(old),
		history: empty(old),
		metrics: empty(old)
	})
}

/** A value the fixture always has; throws if not (instead of a non-null assertion). */
export function must<T>(value: T | null | undefined): T {
	if (value === null || value === undefined) throw new Error("missing fixture value")
	return value
}
