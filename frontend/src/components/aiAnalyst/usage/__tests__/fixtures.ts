import type { AuthUserRole } from "@/types/auth"
import type {
	TalonBudgetEntry,
	TalonBudgets,
	TalonInvestigationUsage,
	TalonRunTimeline,
	TalonTimelineSpan,
	TalonUsageFigures,
	TalonUsageReport
} from "@/types/talonUsage"
import { AxiosError, AxiosHeaders } from "axios"
import { useAuthStore } from "@/stores/auth"

export const JOB = "copilot-inv-1-1760601600000"

export function figures(cost: string, extra: Partial<TalonUsageFigures> = {}): TalonUsageFigures {
	return {
		responses: 2,
		input_tokens: 1200,
		output_tokens: 300,
		cache_read_tokens: 0,
		cache_write_tokens: 0,
		cost_usd: cost,
		unpriced_responses: 0,
		cost_complete: true,
		failed_attempts: 0,
		...extra
	}
}

/** Two groups of 0.1 and 0.2 whose total, as the API sums it exactly, is 0.3 (a float sum is 0.30000000000000004). */
export function usageReport(extra: Partial<TalonUsageReport> = {}): TalonUsageReport {
	return {
		from: "2026-09-17",
		to: "2026-10-16",
		group_by: "customer",
		customer_code: null,
		groups: [
			{ key: "ACME", ...figures("0.2") },
			{ key: null, ...figures("0.1") }
		],
		truncated: false,
		total: figures("0.3", { responses: 4, input_tokens: 2400, output_tokens: 600 }),
		...extra
	}
}

export function investigationUsage(extra: Partial<TalonInvestigationUsage> = {}): TalonInvestigationUsage {
	return {
		job_id: JOB,
		customer_code: "ACME",
		status: "completed",
		stage_durations_ms: { S5: 61_000, S1: 250, S10: 1_200 },
		runs: [
			{
				run_id: "r-1",
				stage: "S4",
				provider: "anthropic",
				model: "claude-haiku-5-5",
				first_at: "2026-10-16T08:00:00+00:00",
				last_at: "2026-10-16T08:00:02+00:00",
				...figures("0.000412")
			},
			{
				run_id: "r-2",
				stage: "S5",
				provider: "anthropic",
				model: "claude-sonnet-5-5",
				first_at: "2026-10-16T08:00:03+00:00",
				last_at: "2026-10-16T08:01:03+00:00",
				...figures("0.1", { cost_complete: false, unpriced_responses: 1 })
			}
		],
		truncated: false,
		total: figures("0.100412", { cost_complete: false, unpriced_responses: 1 }),
		...extra
	}
}

export function span(id: string, extra: Partial<TalonTimelineSpan> & Record<string, unknown> = {}): TalonTimelineSpan {
	return {
		span_id: id,
		trace_id: `${"0".repeat(31)}1`,
		parent_id: null,
		kind: "AGENT",
		name: "invoke_agent analyst-investigation",
		start_time: "2026-10-16T08:00:00.000000Z",
		end_time: "2026-10-16T08:00:10.000000Z",
		duration_ms: 10_000,
		status_code: "OK",
		stage: "S5",
		role: "analyst",
		model: null,
		tool: null,
		prompt_tokens: null,
		completion_tokens: null,
		total_tokens: null,
		cache_read_tokens: null,
		cache_write_tokens: null,
		...extra
	}
}

export function timeline(spans: TalonTimelineSpan[], extra: Partial<TalonRunTimeline> = {}): TalonRunTimeline {
	return { job_id: JOB, customer_code: "ACME", spans, truncated: false, dropped: 0, note: null, ...extra }
}

export function entry(extra: Partial<TalonBudgetEntry> = {}): TalonBudgetEntry {
	return {
		window: "day",
		period: "2026-10-16",
		limit_usd: null,
		source: "unset",
		spent_usd: "0",
		remaining_usd: null,
		warning: false,
		exhausted: false,
		...extra
	}
}

export function budgets(extra: Partial<TalonBudgets> = {}): TalonBudgets {
	return {
		warn_at: "0.8",
		customers: [
			{
				customer_code: "ACME",
				daily: entry({
					limit_usd: "25",
					source: "override",
					spent_usd: "20.5",
					remaining_usd: "4.5",
					warning: true
				}),
				monthly: entry({
					window: "month",
					period: "2026-10",
					limit_usd: "300",
					source: "default",
					spent_usd: "300.000001",
					remaining_usd: "0",
					warning: true,
					exhausted: true
				})
			}
		],
		user: {
			user_id: "1",
			daily: entry({ limit_usd: "5", source: "default", spent_usd: "0.25", remaining_usd: "4.75" })
		},
		general: { daily: entry({ source: "unset", spent_usd: "1.5" }) },
		...extra
	}
}

export function refused(status: number, detail: string) {
	const headers = new AxiosHeaders()
	return new AxiosError("refused", "ERR_BAD_REQUEST", { headers }, null, {
		status,
		statusText: "",
		data: { detail },
		headers,
		config: { headers }
	})
}

export function signInAs(role: AuthUserRole) {
	const store = useAuthStore()
	store.user = { access_token: "t", username: "u", email: "", role }
	return store
}
