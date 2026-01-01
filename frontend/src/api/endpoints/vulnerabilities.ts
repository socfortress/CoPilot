import type {
    VulnerabilitySearchQuery,
    VulnerabilityReportGenerateRequest,
    VulnerabilityReportGenerateResponse,
    VulnerabilityReportListResponse,
    VulnerabilityReportDeleteResponse,
	VulnerabilitySearchResponse,
} from "@/types/vulnerabilities.d"
import { HttpClient } from "../httpClient"

export default {
    /**
     * Search vulnerabilities directly from Wazuh indexer with filtering and pagination
     */
    searchVulnerabilities(query?: VulnerabilitySearchQuery, signal?: AbortSignal) {
        return HttpClient.get<VulnerabilitySearchResponse>(`/vulnerabilities/search`, {
            params: {
                customer_code: query?.customer_code,
                agent_name: query?.agent_name,
                severity: query?.severity,
                cve_id: query?.cve_id,
                package_name: query?.package_name,
                page: query?.page || 1,
                page_size: query?.page_size || 50,
                include_epss: query?.include_epss !== false
            },
            signal
        })
    },

    /**
     * Generate a vulnerability report (synchronous)
     */
    generateReport(request: VulnerabilityReportGenerateRequest) {
        return HttpClient.post<VulnerabilityReportGenerateResponse>(`/vulnerabilities/reports/generate`, request)
    },

    /**
     * Generate a vulnerability report (background task)
     */
    generateReportBackground(request: VulnerabilityReportGenerateRequest) {
        return HttpClient.post<{
            success: boolean
            message: string
            report_id: number
            report_name: string
            customer_code: string
            status: string
            check_status_url: string
            download_url: string
        }>(`/vulnerabilities/reports/generate/background`, request)
    },

    /**
     * List all vulnerability reports
     */
    listReports(customer_code?: string) {
        return HttpClient.get<VulnerabilityReportListResponse>(`/vulnerabilities/reports`, {
            params: customer_code ? { customer_code } : undefined
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
        return HttpClient.delete<VulnerabilityReportDeleteResponse>(`/vulnerabilities/reports/${reportId}`)
    }
}
