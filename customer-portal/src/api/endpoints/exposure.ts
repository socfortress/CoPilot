import type { CommonResponse } from "@/types/common"
import type {
	CveDetail,
	ExposureAvailability,
	ExposureCompliance,
	ExposureSeverity,
	ExposureVulnerabilities,
	PolicyAgents,
	VulnerabilityQuery
} from "@/types/exposure"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

function vulnerabilityParams({ severity, search, page, pageSize }: VulnerabilityQuery) {
	return {
		...(severity ? { severity } : {}),
		...(search?.trim() ? { search: search.trim() } : {}),
		...(page ? { page } : {}),
		...(pageSize ? { page_size: pageSize } : {})
	}
}

export default {
	/**
	 * Whether the Exposure page is on for the caller (any of their customers) or for one
	 * customer (#1289). Cheap on purpose: the menu asks it before offering the page.
	 */
	getAvailability(customerCode?: string) {
		return HttpClient.get<CommonResponse<ExposureAvailability>>("/customer_portal/exposure/availability", {
			params: customerCode ? { customer_code: customerCode } : undefined,
			// Cached as a shared promise (useExposureAvailability): one cancelled by a navigation
			// would never settle and keep the menu entry hidden for the session.
			keepOnNavigation: true
		})
	},

	/** Counts per severity, totals and one page of CVEs across the caller's agents. */
	getVulnerabilities(query: VulnerabilityQuery, customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<ExposureVulnerabilities>>(
			"/customer_portal/exposure/vulnerabilities",
			withCustomerCodes(customerCodes, { params: vulnerabilityParams(query), signal })
		)
	},

	/** One CVE and the caller's agents it affects. */
	getCve(cveId: string, customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<CveDetail>>(
			`/customer_portal/exposure/vulnerabilities/cve/${encodeURIComponent(cveId)}`,
			withCustomerCodes(customerCodes, { signal })
		)
	},

	/** Every finding under the filter as CSV; `x-export-truncated` says when it was cut at its limit. */
	exportVulnerabilities(query: { severity?: ExposureSeverity | null; search?: string | null }, customerCodes?: string[]) {
		return HttpClient.get<Blob>(
			"/customer_portal/exposure/vulnerabilities/export",
			withCustomerCodes(customerCodes, { params: vulnerabilityParams(query), responseType: "blob", keepOnNavigation: true })
		)
	},

	/** SCA across the caller's agents, by policy. */
	getCompliance(customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<ExposureCompliance>>(
			"/customer_portal/exposure/compliance",
			withCustomerCodes(customerCodes, { signal })
		)
	},

	/** The caller's agents assessed on one policy, weakest first. */
	getPolicyAgents(policyId: string, customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<PolicyAgents>>(
			`/customer_portal/exposure/compliance/${encodeURIComponent(policyId)}/agents`,
			withCustomerCodes(customerCodes, { signal })
		)
	}
}
