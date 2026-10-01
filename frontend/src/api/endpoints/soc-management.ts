import type { FlaskBaseResponse } from "@/types/flask"
import type {
	AttentionItem,
	ItemSla,
	PolicyMatrix,
	PolicyOverride,
	PolicyUpdatePayload,
	SlaEntity,
	SlaState,
	SocBucket,
	SocDashboard
} from "@/types/soc-management"
import { HttpClient } from "../http-client"

// SOC Management & SLA (#1187). Admin/analyst only; every figure is narrowed server-side
// to what the caller may see, and per-analyst rows are the admin's view.

export interface SocScopeQuery {
	customerCodes?: string[]
	severities?: string[]
	sources?: string[]
}

export interface SocDashboardQuery extends SocScopeQuery {
	dateFrom: Date
	dateTo: Date
	bucket?: SocBucket
}

export interface SocAttentionQuery extends SocScopeQuery {
	entity?: SlaEntity
	state?: Extract<SlaState, "breached" | "at_risk">
	limit?: number
}

/** Query params with empty filters dropped: an absent filter means "all", never "none". */
export function scopeParams(query: SocScopeQuery): Record<string, string[]> {
	const params: Record<string, string[]> = {}
	if (query.customerCodes?.length) params.customer_codes = query.customerCodes
	if (query.severities?.length) params.severities = query.severities
	if (query.sources?.length) params.sources = query.sources
	return params
}

/** UTC instants: the backend stores naive UTC and converts an offset-carrying value. */
export function periodParams(query: Pick<SocDashboardQuery, "dateFrom" | "dateTo">) {
	return { date_from: query.dateFrom.toISOString(), date_to: query.dateTo.toISOString() }
}

export default {
	getDashboard(query: SocDashboardQuery, signal?: AbortSignal) {
		return HttpClient.get<SocDashboard & FlaskBaseResponse>("/soc_management/dashboard", {
			params: {
				...periodParams(query),
				...scopeParams(query),
				...(query.bucket ? { bucket: query.bucket } : {})
			},
			signal
		})
	},
	getAttention(query: SocAttentionQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { items: AttentionItem[]; total: number }>(
			"/soc_management/attention",
			{
				params: {
					...scopeParams(query),
					...(query.entity ? { entity: query.entity } : {}),
					...(query.state ? { state: query.state } : {}),
					limit: query.limit ?? 100
				},
				signal
			}
		)
	},
	getItemSla(entity: SlaEntity, id: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & ItemSla>(`/soc_management/items/${entity}/${id}/sla`, { signal })
	},
	getPolicy(customerCode: string | null, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { policy: PolicyMatrix }>("/soc_management/policies", {
			params: customerCode ? { customer_code: customerCode } : {},
			signal
		})
	},
	getPolicyOverrides(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { overrides: PolicyOverride[] }>(
			"/soc_management/policies/overrides",
			{
				signal
			}
		)
	},
	/** Admin only. Replaces the whole matrix of a scope. */
	savePolicy(payload: PolicyUpdatePayload) {
		return HttpClient.put<FlaskBaseResponse & { policy: PolicyMatrix; retargeted: number }>(
			"/soc_management/policies",
			payload
		)
	},
	/** Admin only. The customer follows the global policy again. */
	deletePolicyOverride(customerCode: string, applyToOpen = false) {
		return HttpClient.delete<FlaskBaseResponse & { policy: PolicyMatrix; retargeted: number }>(
			`/soc_management/policies/${encodeURIComponent(customerCode)}`,
			{ params: applyToOpen ? { apply_to_open: true } : {} }
		)
	},
	downloadReport(query: SocDashboardQuery) {
		return HttpClient.get<Blob>("/soc_management/report", {
			params: { ...periodParams(query), ...scopeParams(query) },
			responseType: "blob",
			// A download outlives the page that started it.
			keepOnNavigation: true
		})
	}
}
