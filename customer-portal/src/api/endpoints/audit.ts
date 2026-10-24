import type { AuditAvailability, AuditLog, AuditQuery } from "@/types/audit"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

function auditParams({ category, userId, since, until, page, pageSize }: AuditQuery) {
	return {
		...(category ? { category } : {}),
		...(userId ? { user_id: userId } : {}),
		...(since ? { since } : {}),
		...(until ? { until } : {}),
		...(page ? { page } : {}),
		...(pageSize ? { page_size: pageSize } : {})
	}
}

export default {
	/**
	 * Whether the caller gets the Audit Log page (#1298): a customer admin of a customer whose SOC
	 * turned it on. Cheap on purpose: the menu asks it before offering the page.
	 */
	getAvailability() {
		return HttpClient.get<CommonResponse<AuditAvailability>>("/customer_portal/audit/availability", {
			// Cached as a shared promise (useAuditAvailability): one cancelled by a navigation would
			// never settle and keep the menu entry hidden for the session.
			keepOnNavigation: true
		})
	},

	/** One page of the log, newest first. */
	getLog(query: AuditQuery, customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AuditLog>>(
			"/customer_portal/audit",
			withCustomerCodes(customerCodes, { params: auditParams(query), signal })
		)
	},

	/** The filtered log as CSV; `x-export-truncated` says when it was cut at its limit. */
	exportLog(query: AuditQuery, customerCodes?: string[]) {
		const { page: _page, pageSize: _pageSize, ...filters } = query
		return HttpClient.get<Blob>(
			"/customer_portal/audit/export",
			withCustomerCodes(customerCodes, { params: auditParams(filters), responseType: "blob", keepOnNavigation: true })
		)
	}
}
