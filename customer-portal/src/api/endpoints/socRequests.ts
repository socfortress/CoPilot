import type { CommonResponse } from "@/types/common"
import type {
	AskOnAlertPayload,
	AskPayload,
	SocRequest,
	SocRequestAvailability,
	SocRequestsList
} from "@/types/socRequests"
import { HttpClient } from "../httpClient"

/** "Ask the SOC" (#1305): the portal user's questions about one alert or case, and asking one. */
export default {
	/** Whether the customer lets its portal users ask the SOC: for one customer, or any of the caller's. */
	getAvailability(customerCode?: string) {
		return HttpClient.get<CommonResponse<SocRequestAvailability>>("/customer_portal/soc_requests/availability", {
			params: customerCode ? { customer_code: customerCode } : undefined,
			// Cached as a shared promise (useSocRequestsAvailability): one cancelled by a navigation
			// would never settle and keep the tab hidden for the session.
			keepOnNavigation: true
		})
	},
	listForAlert(alertId: number, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<SocRequestsList>>(`/customer_portal/soc_requests/alert/${alertId}`, {
			signal
		})
	},
	listForCase(caseId: number, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<SocRequestsList>>(`/customer_portal/soc_requests/case/${caseId}`, {
			signal
		})
	},
	askOnAlert(alertId: number, payload: AskOnAlertPayload) {
		return HttpClient.post<CommonResponse<{ request: SocRequest }>>(
			`/customer_portal/soc_requests/alert/${alertId}`,
			payload
		)
	},
	askOnCase(caseId: number, payload: AskPayload) {
		return HttpClient.post<CommonResponse<{ request: SocRequest }>>(
			`/customer_portal/soc_requests/case/${caseId}`,
			payload
		)
	}
}
