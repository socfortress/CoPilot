import type { AiAlertAnalysis, AiInsights } from "@/types/aiReports"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

export default {
	/**
	 * Read-only AI Analyst findings for a single alert.
	 * The backend enforces the same customer/tag visibility as the alert itself.
	 */
	getAlertAnalysis(alertId: number, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AiAlertAnalysis>>(`/customer_portal/ai_reports/alert/${alertId}`, { signal })
	},

	/**
	 * Aggregate AI report coverage for the overview card.
	 */
	getInsights(customerCodes?: string[], limit = 5, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AiInsights>>(
			"/customer_portal/ai_reports/insights",
			withCustomerCodes(customerCodes, { params: { limit }, signal })
		)
	}
}
