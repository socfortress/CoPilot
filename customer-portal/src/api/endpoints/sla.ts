import type { CommonResponse } from "@/types/common"
import type { SlaAvailability, SlaOverview } from "@/types/sla"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

export default {
	/**
	 * Whether the SLA page is on for the caller (any of their customers) or for one
	 * customer. Cheap on purpose: the menu asks it before offering the page.
	 */
	getAvailability(customerCode?: string) {
		return HttpClient.get<CommonResponse<SlaAvailability>>("/customer_portal/sla/availability", {
			params: customerCode ? { customer_code: customerCode } : undefined,
			// Cached as a shared promise (useSlaAvailability): one cancelled by a navigation
			// would never settle and keep the menu entry hidden for the session.
			keepOnNavigation: true
		})
	},

	/** The SLA figures of the caller's customers over `[dateFrom, dateTo)`. */
	getOverview(dateFrom: Date, dateTo: Date, customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<SlaOverview>>(
			"/customer_portal/sla/overview",
			withCustomerCodes(customerCodes, {
				params: { date_from: dateFrom.toISOString(), date_to: dateTo.toISOString() },
				signal
			})
		)
	}
}
