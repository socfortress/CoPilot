import type { AiAlertAnalysis, AiAnalysisRequest, AiInsights, AiReportAvailability } from "@/types/aiReports"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

export default {
	/**
	 * Whether the AI surfaces should render at all. Cheap on purpose — the portal
	 * asks this before showing the AI Report tab, so it carries no report data.
	 */
	getAvailability(customerCode?: string, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AiReportAvailability>>("/customer_portal/ai_reports/availability", {
			params: customerCode ? { customer_code: customerCode } : undefined,
			signal,
			// Cached as a shared promise (useAiReportsAvailability): one cancelled by a
			// navigation would never settle and pin that customer's AI tab to "loading".
			keepOnNavigation: true
		})
	},

	/**
	 * Read-only AI Analyst findings for a single alert.
	 * The backend enforces the same customer/tag visibility as the alert itself.
	 */
	getAlertAnalysis(alertId: number, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AiAlertAnalysis>>(`/customer_portal/ai_reports/alert/${alertId}`, {
			signal
		})
	},

	/**
	 * Ask the AI analyst to analyse an alert (#1215), where its customer allows it. The
	 * backend refuses while an analysis runs, within 30 minutes of the last one, or over
	 * the customer's daily limit, each with a message meant for the user.
	 */
	requestAnalysis(alertId: number) {
		return HttpClient.post<CommonResponse<AiAnalysisRequest>>(`/customer_portal/ai_reports/alert/${alertId}/investigate`)
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
