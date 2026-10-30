import type { CommonResponse } from "@/types/common"
import type { AlertIocEnrichment, IocEnrichment, IocEnrichmentAvailability } from "@/types/iocEnrichment"
import { HttpClient } from "../httpClient"

/** Threat Intel enrichment of the IOCs of the user's alerts (#1318). */
export default {
	/** Whether the customer lets its portal users check IOCs: for one customer, or any of the caller's. */
	getAvailability(customerCode?: string) {
		return HttpClient.get<CommonResponse<IocEnrichmentAvailability>>("/customer_portal/ioc_enrichment/availability", {
			params: customerCode ? { customer_code: customerCode } : undefined,
			// Cached as a shared promise (useIocEnrichmentAvailability): one cancelled by a navigation
			// would never settle and keep the checks hidden for the session.
			keepOnNavigation: true
		})
	},
	/** What is known about every IOC of an alert: read from what the SOC keeps, no source is asked. */
	getForAlert(alertId: number, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AlertIocEnrichment>>(`/customer_portal/ioc_enrichment/alert/${alertId}`, {
			signal
		})
	},
	/** Check one IOC of an alert against the sources whose answer is missing or old. */
	check(alertId: number, iocId: number) {
		return HttpClient.post<CommonResponse<{ ioc: IocEnrichment }>>(
			`/customer_portal/ioc_enrichment/alert/${alertId}/ioc/${iocId}`
		)
	}
}
