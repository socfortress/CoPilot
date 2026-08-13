import type { FlaskBaseResponse } from "@/types/flask"
import type {
	IncidentCustomerReportGenerateBackgroundResponse,
	IncidentCustomerReportGenerateRequest,
	IncidentCustomerReportListResponse
} from "@/types/incidentReports"
import { HttpClient } from "../http-client"

export default {
	/**
	 * Queue generation of a customer Incident-Management PDF report (background task)
	 */
	generateReportBackground(request: IncidentCustomerReportGenerateRequest) {
		return HttpClient.post<FlaskBaseResponse & IncidentCustomerReportGenerateBackgroundResponse>(
			`/incidents/customer_reports/generate/background`,
			request
		)
	},

	/**
	 * List customer Incident-Management reports (optionally filtered by customer)
	 */
	listReports(customer_code: string | null, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & IncidentCustomerReportListResponse>(`/incidents/customer_reports`, {
			params: customer_code ? { customer_code } : undefined,
			signal
		})
	},

	/**
	 * Download a customer Incident-Management report PDF
	 */
	downloadReport(reportId: number) {
		return HttpClient.get<Blob>(`/incidents/customer_reports/${reportId}/download`, {
			responseType: "blob"
		})
	},

	/**
	 * Delete a customer Incident-Management report
	 */
	deleteReport(reportId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/customer_reports/${reportId}`)
	},

	/**
	 * Set whether an analyst/admin report is visible to the customer portal (analyst/admin only)
	 */
	setVisibility(reportId: number, visible: boolean) {
		return HttpClient.patch<FlaskBaseResponse & { visible_to_customer: boolean }>(
			`/incidents/customer_reports/${reportId}/visibility`,
			{ visible }
		)
	}
}
