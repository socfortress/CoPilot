import type { FlaskBaseResponse } from "@/types/flask"
import type {
	VulnerabilityReportDeleteResponse,
	VulnerabilityReportGenerateBackgroundResponse,
	VulnerabilityReportGenerateRequest,
	VulnerabilityReportGenerateResponse,
	VulnerabilityReportListResponse,
	VulnerabilitySearchQuery,
	VulnerabilitySearchResponse
} from "@/types/vulnerabilities"
import { HttpClient } from "../http-client"

export default {
	/**
	 * Search vulnerabilities directly from Wazuh indexer with filtering and pagination
	 */
	searchVulnerabilities(query: VulnerabilitySearchQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & VulnerabilitySearchResponse>(`/vulnerabilities/search`, {
			params: {
				customer_code: query.customer_code,
				agent_name: query.agent_name,
				severity: query.severity,
				cve_id: query.cve_id,
				package_name: query.package_name,
				page: query.page || 1,
				page_size: query.page_size || 50,
				include_epss: query.include_epss !== false
			},
			signal
		})
	},

	/**
	 * Generate a vulnerability report (synchronous)
	 */
	generateReport(request: VulnerabilityReportGenerateRequest) {
		return HttpClient.post<FlaskBaseResponse & VulnerabilityReportGenerateResponse>(
			`/vulnerabilities/reports/generate`,
			request
		)
	},

	/**
	 * Generate a vulnerability report (background task)
	 */
	generateReportBackground(request: VulnerabilityReportGenerateRequest) {
		return HttpClient.post<FlaskBaseResponse & VulnerabilityReportGenerateBackgroundResponse>(
			`/vulnerabilities/reports/generate/background`,
			request
		)
	},

	/**
	 * List all vulnerability reports
	 */
	listReports(customer_code?: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & VulnerabilityReportListResponse>(`/vulnerabilities/reports`, {
			params: customer_code ? { customer_code } : undefined,
			signal
		})
	},

	/**
	 * Download a vulnerability report
	 */
	downloadReport(reportId: number) {
		return HttpClient.get<Blob>(`/vulnerabilities/reports/${reportId}/download`, {
			responseType: "blob"
		})
	},

	/**
	 * Delete a vulnerability report
	 */
	deleteReport(reportId: number) {
		return HttpClient.delete<FlaskBaseResponse & VulnerabilityReportDeleteResponse>(
			`/vulnerabilities/reports/${reportId}`
		)
	}
}
