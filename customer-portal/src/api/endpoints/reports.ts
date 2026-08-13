import type { CommonResponse } from "@/types/common"
import type {
	IncidentCustomerReportGenerateBackgroundResponse,
	IncidentCustomerReportGenerateRequest,
	IncidentCustomerReportListResponse
} from "@/types/reports"
import { HttpClient } from "../httpClient"

export default {
	/**
	 * List Incident-Management reports the current customer can access.
	 *
	 * The backend scopes results to the authenticated user's accessible
	 * customers, so no customer filter is sent from the portal.
	 */
	listReports(signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<IncidentCustomerReportListResponse>>("/incidents/customer_reports", {
			signal
		})
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
			responseType: "blob"
		})
	},

	/**
	 * Delete a report
	 */
	deleteReport(reportId: number) {
		return HttpClient.delete<CommonResponse>(`/incidents/customer_reports/${reportId}`)
	}
}
