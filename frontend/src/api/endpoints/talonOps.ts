import type {
	TalonOpsFindingPage,
	TalonOpsFindingResponse,
	TalonOpsJobs,
	TalonOpsQuery,
	TalonOpsRunNow,
	TalonOpsRuns,
	TalonOpsRunsQuery,
	TalonOpsSummary,
	TalonOpsSummaryQuery
} from "@/types/talonOps"
import axios from "axios"
import { HttpClient } from "../http-client"
import { refusalDetail } from "./talonV2"

/**
 * The Talon Ops tab (`/api/talon/ops/...`): talon-analyst's ops findings (endpoints, log sources,
 * storage and noise, the indexer cluster and its disks, mappings, agent versions, exclusion candidates),
 * its ops jobs and their runs. Every route answers 404 `{"detail": "Not Found"}` while the
 * "Talon v2" setting is off, so nothing here is called unless `useTalonV2Availability` said it is on.
 * CoPilot sends talon-analyst the signed-in user's identity and checks every finding's customer; the
 * actor of an action is the signed-in user (no field here names one). Run now is an admin's. A refusal
 * is `{"detail", "code"}` (`opsFailure` reads it).
 */

export type TalonOpsFailureCode =
	| "v2_off"
	| "unsupported"
	| "not_found"
	| "forbidden"
	| "invalid"
	| "conflict"
	| "unavailable"
	| "bad_answer"
	| "unknown"

export interface TalonOpsFailure {
	status: number | null
	code: TalonOpsFailureCode
	detail: string
}

const CODES: TalonOpsFailureCode[] = [
	"unsupported",
	"not_found",
	"forbidden",
	"invalid",
	"conflict",
	"unavailable",
	"bad_answer"
]

/** Why a request failed. CoPilot's own 404 while "Talon v2" is off is `{"detail": "Not Found"}` with no code. */
export function opsFailure(err: unknown): TalonOpsFailure {
	if (axios.isAxiosError(err) && err.response) {
		const data = err.response.data as { detail?: unknown; code?: unknown } | undefined
		const status = err.response.status
		const code = typeof data?.code === "string" && (CODES as string[]).includes(data.code) ? data.code : null
		if (status === 404 && !code && data?.detail === "Not Found") {
			return { status, code: "v2_off", detail: "Talon v2 is off in CoPilot" }
		}
		return { status, code: (code as TalonOpsFailureCode) ?? "unknown", detail: refusalDetail(data) }
	}
	return { status: null, code: "unknown", detail: refusalDetail(null) }
}

function params(query: TalonOpsQuery | TalonOpsRunsQuery | TalonOpsSummaryQuery): Record<string, string | number> {
	const out: Record<string, string | number> = {}
	for (const [key, value] of Object.entries(query)) {
		if (value === null || value === undefined || value === "" || value === false) continue
		out[key] = value === true ? "true" : (value as string | number)
	}
	return out
}

/** The finding's stored customer, sent back so CoPilot and Talon check it is still the same one. */
function customerParam(customerCode: string | null | undefined) {
	return customerCode ? { customer_code: customerCode } : undefined
}

export default {
	listFindings(query: TalonOpsQuery, signal?: AbortSignal) {
		return HttpClient.get<TalonOpsFindingPage>(`/talon/ops/findings`, { params: params(query), signal })
	},
	/** Open finding counts by severity, job and customer: the caller's customers only (CoPilot checks). */
	summary(query: TalonOpsSummaryQuery, signal?: AbortSignal) {
		return HttpClient.get<TalonOpsSummary>(`/talon/ops/summary`, { params: params(query), signal })
	},
	getFinding(id: number, customerCode?: string | null, signal?: AbortSignal) {
		return HttpClient.get<TalonOpsFindingResponse>(`/talon/ops/findings/${Number(id)}`, {
			params: customerParam(customerCode),
			signal
		})
	},
	/** Audited; the actor is the signed-in user. */
	acknowledge(id: number, customerCode?: string | null) {
		return HttpClient.post<TalonOpsFindingResponse>(`/talon/ops/findings/${Number(id)}/acknowledge`, undefined, {
			params: customerParam(customerCode)
		})
	},
	/** `until` must be in the future and at most 90 days away (the backend checks). Audited. */
	mute(id: number, until: string, customerCode?: string | null) {
		return HttpClient.post<TalonOpsFindingResponse>(
			`/talon/ops/findings/${Number(id)}/mute`,
			{ until },
			{ params: customerParam(customerCode) }
		)
	},
	/** Audited. */
	reopen(id: number, customerCode?: string | null) {
		return HttpClient.post<TalonOpsFindingResponse>(`/talon/ops/findings/${Number(id)}/reopen`, undefined, {
			params: customerParam(customerCode)
		})
	},
	listJobs(signal?: AbortSignal) {
		return HttpClient.get<TalonOpsJobs>(`/talon/ops/jobs`, { signal })
	},
	/** Recent runs of the caller's customers (platform runs for an admin), newest first. */
	listRuns(query: TalonOpsRunsQuery, signal?: AbortSignal) {
		return HttpClient.get<TalonOpsRuns>(`/talon/ops/runs`, { params: params(query), signal })
	},
	/** Admin only (the backend checks the database role). Audited. */
	runNow(name: string) {
		return HttpClient.post<TalonOpsRunNow>(`/talon/ops/jobs/${encodeURIComponent(name)}/run`)
	}
}
