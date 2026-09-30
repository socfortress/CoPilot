import type { CommonResponse } from "@/types/common"
import type {
	IncidentCustomerReportGenerateBackgroundResponse,
	IncidentCustomerReportGenerateRequest,
	IncidentCustomerReportListResponse
} from "@/types/reports"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

export default {
	/**
	 * List Incident-Management reports the current customer can access.
	 *
	 * The backend scopes results to the user's accessible customers; `customerCodes`
	 * (the global customer filter) narrows them further, never widens them.
	 */
	listReports(options: { customerCodes?: string[]; signal?: AbortSignal; keepOnNavigation?: boolean } = {}) {
		const { customerCodes, signal, keepOnNavigation = false } = options
		return HttpClient.get<CommonResponse<IncidentCustomerReportListResponse>>(
			"/incidents/customer_reports",
			withCustomerCodes(customerCodes, { signal, keepOnNavigation })
		)
	},

	/**
	 * Queue generation of a customer Incident-Management PDF report (background task)
	 */
	generateReportBackground(request: IncidentCustomerReportGenerateRequest) {
		return HttpClient.post<CommonResponse<IncidentCustomerReportGenerateBackgroundResponse>>(
			"/incidents/customer_reports/generate/background",
			request
		)
	},

	/**
	 * Download a report PDF
	 */
	downloadReport(reportId: number) {
		return HttpClient.get<Blob>(`/incidents/customer_reports/${reportId}/download`, {
			responseType: "blob",
			keepOnNavigation: true
		})
	},

	/**
	 * Delete a report
	 */
	deleteReport(reportId: number) {
		return HttpClient.delete<CommonResponse>(`/incidents/customer_reports/${reportId}`)
	}
}
