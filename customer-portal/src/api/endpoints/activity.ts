import type { Activity, ActivityAvailability, ActivityRange } from "@/types/activity"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

export default {
	/**
	 * Whether the Activity page is on for the caller (any of their customers) or for one
	 * customer (#1284). Cheap on purpose: the menu asks it before offering the page.
	 */
	getAvailability(customerCode?: string) {
		return HttpClient.get<CommonResponse<ActivityAvailability>>("/customer_portal/activity/availability", {
			params: customerCode ? { customer_code: customerCode } : undefined,
			// Cached as a shared promise (useActivityAvailability): one cancelled by a navigation
			// would never settle and keep the menu entry hidden for the session.
			keepOnNavigation: true
		})
	},

	/** What the SOC handled for the caller's customers over the last `range`, and the period before. */
	getActivity(range: ActivityRange, customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<Activity>>(
			"/customer_portal/activity",
			withCustomerCodes(customerCodes, { params: { range }, signal })
		)
	}
}
