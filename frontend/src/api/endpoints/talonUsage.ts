import type {
	TalonBudgets,
	TalonBudgetUpdate,
	TalonCustomerBudget,
	TalonInvestigationUsage,
	TalonRunTimeline,
	TalonThreadUsage,
	TalonUsageQuery,
	TalonUsageReport
} from "@/types/talonUsage"
import axios from "axios"
import { HttpClient } from "../http-client"
import { refusalDetail } from "./talonV2"

/**
 * Talon v2 cost and run views (talon-analyst M5-9; CoPilot M5-9a): usage, budgets and an
 * investigation's run timeline, through CoPilot's routes under `/api/talon/v2`.
 *
 * Every route answers 404 while the "Talon v2" setting is off, so nothing here is called unless
 * `useTalonV2Availability` said it is on (and the run view only when it also said `runView`).
 * Answers are relayed as talon-analyst wrote them: amounts are decimal strings. A refusal is
 * `{"detail": <fixed text>}` with its status (`talonFailure` reads it).
 */

/** Why a request failed: its status (null: no answer) and the short text to show. */
export interface TalonFailure {
	status: number | null
	detail: string
}

export function talonFailure(err: unknown): TalonFailure {
	if (axios.isAxiosError(err) && err.response) {
		return { status: err.response.status, detail: refusalDetail(err.response.data) }
	}
	return { status: null, detail: refusalDetail(null) }
}

export default {
	/** Tokens and cost per group over whole UTC days (`from`/`to` `YYYY-MM-DD`, both included, at most 366 days). */
	getUsage(query: TalonUsageQuery, signal?: AbortSignal) {
		const params: Record<string, string> = { from: query.from, to: query.to }
		if (query.group_by) params.group_by = query.group_by
		if (query.customer_code) params.customer_code = query.customer_code
		return HttpClient.get<TalonUsageReport>(`/talon/v2/usage`, { params, signal })
	},
	/** One investigation's cost per run, stage and model, with its stage durations. `jobId` is CoPilot's `ai_analyst_job.id`. */
	getInvestigationUsage(jobId: string, signal?: AbortSignal) {
		return HttpClient.get<TalonInvestigationUsage>(`/talon/v2/usage/investigations/${encodeURIComponent(jobId)}`, {
			signal
		})
	},
	/** One of the caller's own v2 threads' cost. */
	getThreadUsage(threadId: string, signal?: AbortSignal) {
		return HttpClient.get<TalonThreadUsage>(`/talon/v2/usage/threads/${encodeURIComponent(threadId)}`, { signal })
	},
	/** Every customer's daily and monthly budget (admin only; the backend refuses anyone else). */
	getBudgets(customerCode?: string | null, signal?: AbortSignal) {
		const params = customerCode ? { customer_code: customerCode } : undefined
		return HttpClient.get<TalonBudgets>(`/talon/v2/budgets`, { params, signal })
	},
	/** Replace one customer's override (admin only, audited). Answers the customer's budgets as now set. */
	putBudget(customerCode: string, body: TalonBudgetUpdate) {
		return HttpClient.put<TalonCustomerBudget>(`/talon/v2/budgets/${encodeURIComponent(customerCode)}`, {
			daily_usd: body.daily_usd,
			monthly_usd: body.monthly_usd
		})
	},
	/** One investigation's run timeline from Phoenix (span names, kinds, times, status and tokens only). */
	getRunTimeline(jobId: string, signal?: AbortSignal) {
		return HttpClient.get<TalonRunTimeline>(`/talon/v2/runs/${encodeURIComponent(jobId)}/timeline`, { signal })
	}
}
