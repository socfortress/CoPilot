import type { FlaskBaseResponse } from "@/types/flask"
import type {
	ScaOverviewQuery,
	ScaOverviewResponse,
	ScaPackageAgentsResponse,
	ScaPackageRegistryResponse,
	ScaPoliciesIndexResponse,
	ScaPolicyContentResponse,
	SCAReportGenerateRequest,
	SCAReportGenerateResponse,
	SCAReportListResponse,
	ScaStatsResponse
} from "@/types/sca"
import { HttpClient } from "../httpClient"
import { createSSEStream } from "../sseClient"

export default {
	/**
	 * Search SCA results across all agents with filtering and pagination
	 */
	searchScaOverview(query: ScaOverviewQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & ScaOverviewResponse>(`/sca/overview`, {
			params: {
				customer_code: query.customer_code,
				agent_name: query.agent_name,
				policy_id: query.policy_id,
				policy_name: query.policy_name,
				min_score: query.min_score,
				max_score: query.max_score,
				page: query.page || 1,
				page_size: query.page_size || 50
			},
			signal
		})
	},

	/**
	 * Stream SCA results using SSE client (token + params gestiti automaticamente)
	 */
	async streamScaOverview(
		query: ScaOverviewQuery,
		handlers: {
			onStart?: (data: any) => void
			onAgentResult?: (data: any) => void
			onAgentEmpty?: (data: any) => void
			onProgress?: (data: any) => void
			onComplete?: (data: any) => void
			onError?: (error: any) => void
		},
		abortController?: AbortController
	): Promise<void> {
		await createSSEStream({
			path: "/sca/overview/stream",
			params: query
				? {
						customer_code: query.customer_code,
						agent_name: query.agent_name,
						policy_id: query.policy_id,
						policy_name: query.policy_name,
						min_score: query.min_score,
						max_score: query.max_score
					}
				: undefined,
			signal: abortController?.signal,
			handlers: {
				start: data => handlers.onStart?.(data),
				agent_result: data => handlers.onAgentResult?.(data),
				agent_empty: data => handlers.onAgentEmpty?.(data),
				progress: data => handlers.onProgress?.(data),
				complete: data => handlers.onComplete?.(data),
				error: data => handlers.onError?.(data),
				agent_error: data => handlers.onError?.(data),
				onError: err => handlers.onError?.(err)
			}
		})
	},

	/**
	 * Get SCA statistics
	 */
	getScaStats(customer_code?: string) {
		return HttpClient.get<FlaskBaseResponse & ScaStatsResponse>(`/sca/stats`, {
			params: customer_code ? { customer_code } : undefined
		})
	},

	/**
	 * Generate an SCA report (synchronous)
	 */
	generateReport(request: SCAReportGenerateRequest) {
		return HttpClient.post<FlaskBaseResponse & SCAReportGenerateResponse>(`/sca/reports/generate`, request)
	},

	/**
	 * List all SCA reports
	 */
	listReports(customer_code?: string) {
		return HttpClient.get<FlaskBaseResponse & SCAReportListResponse>(`/sca/reports`, {
			params: customer_code ? { customer_code } : undefined
		})
	},

	/**
	 * Download an SCA report
	 */
	downloadReport(reportId: number) {
		return HttpClient.get<Blob>(`/sca/reports/${reportId}/download`, {
			responseType: "blob"
		})
	},

	/**
	 * Delete an SCA report
	 */
	deleteReport(reportId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/sca/reports/${reportId}`)
	},

	/**
	 * List all available SCA policies from the CoPilot-SCA repository
	 */
	getPolicies() {
		return HttpClient.get<FlaskBaseResponse & ScaPoliciesIndexResponse>(`/sca/policies`)
	},

	/**
	 * Fetch the YAML content of a specific SCA policy
	 */
	getPolicyContent(policyId: string) {
		return HttpClient.get<FlaskBaseResponse & ScaPolicyContentResponse>(`/sca/policies/${policyId}`)
	},

	/**
	 * List all tracked SCA-relevant package categories
	 */
	getPackageRegistry() {
		return HttpClient.get<FlaskBaseResponse & ScaPackageRegistryResponse>(`/sca/packages/registry`)
	},

	/**
	 * Detect agents running a tracked SCA-relevant package
	 */
	getAgentsForPackage(registryKey: string) {
		return HttpClient.get<FlaskBaseResponse & ScaPackageAgentsResponse>(
			`/sca/packages/registry/${registryKey}/agents`
		)
	}
}
