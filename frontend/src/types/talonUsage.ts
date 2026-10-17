/**
 * Talon v2 usage, budgets and the run view, as CoPilot's proxy relays them (talon-analyst SPEC §13.5
 * FR-COST-4/5 as built, §5.4; CoPilot `services/talon_usage.py`, `services/talon_runs.py`,
 * `schema/talon_runs.py`).
 *
 * Every amount of money is a **decimal string** (`"0.000123"`, `"12.5"`): the ledger's exact sum,
 * shown as the API wrote it. Never add, round or reformat it with floats; a chart may parse it to
 * draw a bar, nothing else.
 */

export type TalonUsageGroupBy = "customer" | "model" | "provider" | "role" | "stage" | "day" | "user"

/** The figures of every group, run and total (`talon.api.usage._figures`). */
export interface TalonUsageFigures {
	responses: number
	input_tokens: number
	output_tokens: number
	cache_read_tokens: number
	cache_write_tokens: number
	/** A decimal string. */
	cost_usd: string
	/** Responses nothing priced: counted, their tokens included, their cost not known. */
	unpriced_responses: number
	/** False when any response in it was unpriced: the cost is a lower bound. */
	cost_complete: boolean
	/** Failed fallback attempts (billed, so included). */
	failed_attempts: number
}

export interface TalonUsageGroup extends TalonUsageFigures {
	/** The group's value; null for a row without that column (general chat under `customer`, the investigations under `user`). */
	key: string | null
	/** An admin's `group_by=user`: CoPilot's username for that user id (CoPilot adds it). */
	username?: string | null
}

export interface TalonUsageReport {
	from: string
	to: string
	group_by: TalonUsageGroupBy
	customer_code: string | null
	groups: TalonUsageGroup[]
	/** More than 1000 groups exist; the total still covers every row. */
	truncated: boolean
	total: TalonUsageFigures
}

export interface TalonUsageQuery {
	from: string
	to: string
	group_by?: TalonUsageGroupBy
	customer_code?: string | null
}

export interface TalonInvestigationRun extends TalonUsageFigures {
	run_id: string | null
	stage: string | null
	provider: string | null
	model: string | null
	first_at: string | null
	last_at: string | null
}

export interface TalonInvestigationUsage {
	job_id: string
	customer_code: string
	status: string
	/** Each stage's duration in milliseconds (`investigation_event`; S0 has none). */
	stage_durations_ms: Record<string, number>
	runs: TalonInvestigationRun[]
	truncated: boolean
	total: TalonUsageFigures
}

export interface TalonThreadUsageGroup extends TalonUsageFigures {
	stage: string | null
	provider: string | null
	model: string | null
}

export interface TalonThreadUsage {
	thread_id: string
	customer_code: string | null
	groups: TalonThreadUsageGroup[]
	truncated: boolean
	total: TalonUsageFigures
}

/** Where a ceiling comes from: a `TALON_BUDGET_*` setting, an admin's override, an admin's "unlimited", or nothing. */
export type TalonBudgetSource = "default" | "override" | "unlimited" | "unset"

/** One budget window now (`talon.budgets._entry`). */
export interface TalonBudgetEntry {
	window: string
	period: string
	/** A decimal string; null means no limit. */
	limit_usd: string | null
	source: TalonBudgetSource
	/** Decimal strings; null for anyone but an admin (decision C), and the remaining with no limit. */
	spent_usd: string | null
	remaining_usd: string | null
	/** At 80% of the ceiling. */
	warning: boolean
	exhausted: boolean
}

export interface TalonCustomerBudget {
	customer_code: string
	daily: TalonBudgetEntry
	monthly: TalonBudgetEntry
}

export interface TalonBudgets {
	warn_at: string
	customers: TalonCustomerBudget[]
	/** The caller's own daily chat budget. */
	user: { user_id: string; daily: TalonBudgetEntry }
	/** General (unscoped) chat's daily budget, for an admin. */
	general: { daily: TalonBudgetEntry } | null
}

/** `null` (the default applies), `"unlimited"`, or a positive decimal string such as `"25"` or `"12.50"`. */
export type TalonBudgetAmount = string | null

export interface TalonBudgetUpdate {
	daily_usd: TalonBudgetAmount
	monthly_usd: TalonBudgetAmount
}

/** One span of the run view: the allowlist DTO (`schema/talon_runs.py:TimelineSpan`), nothing else. */
export interface TalonTimelineSpan {
	span_id: string
	trace_id: string
	parent_id: string | null
	kind: string
	name: string
	start_time: string
	end_time: string
	duration_ms: number
	status_code: string
	stage: string | null
	role: string | null
	model: string | null
	tool: string | null
	prompt_tokens: number | null
	completion_tokens: number | null
	total_tokens: number | null
	cache_read_tokens: number | null
	cache_write_tokens: number | null
}

export interface TalonRunTimeline {
	job_id: string
	customer_code: string
	spans: TalonTimelineSpan[]
	/** More spans exist than were read. */
	truncated: boolean
	/** Spans Phoenix returned that weren't this job's and customer's, didn't parse, or repeated: never shown. */
	dropped: number
	/** Why there is nothing to show, when known (`"no trace data"`). */
	note: string | null
}
