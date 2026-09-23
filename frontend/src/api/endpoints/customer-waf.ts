import type {
	CustomerWafBlock,
	CustomerWafBlockAction,
	CustomerWafBlockPayload,
	CustomerWafEvent,
	CustomerWafEventsQuery,
	CustomerWafInstance,
	CustomerWafPayload,
	CustomerWafSite,
	CustomerWafStats,
	CustomerWafThreatIntelEntry,
	CustomerWafThreatIntelSummary,
	CustomerWafVerification
} from "@/types/customer-waf"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

// A customer's SOCFortress WAFs (#1165). Upstream WAF failures come back as 502/409 with a
// `reason` — never 401/403 — so they surface as ordinary errors, not a session logout.
const base = (customerCode: string) => `/customer_waf/${encodeURIComponent(customerCode)}`

export default {
	/** WAFs across every customer the caller can see — the WAF page's pickers. */
	getAllInstances(signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & { instances: CustomerWafInstance[]; encryption_key_configured: boolean }
		>("/customer_waf", { signal })
	},
	getInstances(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & { instances: CustomerWafInstance[]; encryption_key_configured: boolean }
		>(base(customerCode), { signal })
	},
	/** Admin only. Saves, then runs a connection test (the save stands even if it fails). */
	createInstance(customerCode: string, payload: CustomerWafPayload) {
		return HttpClient.post<
			FlaskBaseResponse & {
				instance: CustomerWafInstance
				verification: CustomerWafVerification | null
				warnings: string[]
			}
		>(base(customerCode), payload)
	},
	/** Admin only. A blank `service_token` keeps the stored one. */
	updateInstance(customerCode: string, wafId: number, payload: Partial<CustomerWafPayload>) {
		return HttpClient.put<
			FlaskBaseResponse & {
				instance: CustomerWafInstance
				verification: CustomerWafVerification | null
				warnings: string[]
			}
		>(`${base(customerCode)}/${wafId}`, payload)
	},
	/** Admin only. Removes CoPilot's copy; the token stays valid on the WAF until revoked there. */
	deleteInstance(customerCode: string, wafId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`${base(customerCode)}/${wafId}`)
	},
	verifyInstance(customerCode: string, wafId: number) {
		return HttpClient.post<
			FlaskBaseResponse & { instance: CustomerWafInstance; verification: CustomerWafVerification }
		>(`${base(customerCode)}/${wafId}/verify`)
	},
	getSites(customerCode: string, wafId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { sites: CustomerWafSite[] }>(`${base(customerCode)}/${wafId}/sites`, {
			signal
		})
	},
	getEvents(customerCode: string, wafId: number, query: CustomerWafEventsQuery = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { events: CustomerWafEvent[]; limit: number; offset: number }>(
			`${base(customerCode)}/${wafId}/events`,
			{ params: query, signal }
		)
	},
	getStats(customerCode: string, wafId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { stats: CustomerWafStats }>(`${base(customerCode)}/${wafId}/stats`, {
			signal
		})
	},
	getThreatIntel(customerCode: string, wafId: number, signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & { summary: CustomerWafThreatIntelSummary; entries: CustomerWafThreatIntelEntry[] }
		>(`${base(customerCode)}/${wafId}/threat-intel`, { signal })
	},
	getBlocks(customerCode: string, wafId: number, signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & { copilot_blocks: CustomerWafBlock[]; other_ip_blocks: CustomerWafBlock[] }
		>(`${base(customerCode)}/${wafId}/blocks`, { signal })
	},
	/** Idempotent: an IP already blocked (by CoPilot or the WAF's own rule) is reported, not re-blocked. */
	block(customerCode: string, wafId: number, payload: CustomerWafBlockPayload) {
		return HttpClient.post<
			FlaskBaseResponse & {
				action: CustomerWafBlockAction
				target: string
				block: CustomerWafBlock
				warnings: string[]
			}
		>(`${base(customerCode)}/${wafId}/blocks`, payload)
	},
	/** Disables CoPilot's rule for exactly this target (never deletes, never touches WAF-owned rules). */
	unblock(customerCode: string, wafId: number, target: string) {
		return HttpClient.delete<
			FlaskBaseResponse & { action: "unblocked" | "already_unblocked"; target: string; blocks: CustomerWafBlock[] }
		>(`${base(customerCode)}/${wafId}/blocks`, { params: { target } })
	}
}
