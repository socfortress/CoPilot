import type {
    AvailableChecksResponse,
    DeleteResponse,
    GitHubAuditBaselineCreate,
    GitHubAuditBaselineResponse,
    GitHubAuditConfigCreate,
    GitHubAuditConfigResponse,
    GitHubAuditConfigUpdate,
    GitHubAuditExclusionCreate,
    GitHubAuditExclusionResponse,
    GitHubAuditExclusionUpdate,
    GitHubAuditReportListResponse,
    GitHubAuditReportResponse,
    GitHubAuditRequest,
    GitHubAuditResponse,
    GitHubAuditSummaryResponse
} from "@/types/githubAudit.d"
import { HttpClient } from "../httpClient"

const BASE_PATH = "/github-audit"

export default {
    // ==================== Configuration Endpoints ====================

    /**
     * Create a new GitHub Audit configuration
     */
    createConfig(config: GitHubAuditConfigCreate, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditConfigResponse>(`${BASE_PATH}/config`, config, { signal })
    },

    /**
     * Get all GitHub Audit configurations
     */
    getConfigs(customerCode?: string, signal?: AbortSignal) {
        const params = customerCode ? { customer_code: customerCode } : undefined
        return HttpClient.get<GitHubAuditConfigResponse>(`${BASE_PATH}/config`, { params, signal })
    },

    /**
     * Get a specific GitHub Audit configuration by ID
     */
    getConfig(configId: number, signal?: AbortSignal) {
        return HttpClient.get<GitHubAuditConfigResponse>(`${BASE_PATH}/config/${configId}`, {
            signal
        })
    },

    /**
     * Update a GitHub Audit configuration
     */
    updateConfig(configId: number, config: GitHubAuditConfigUpdate, signal?: AbortSignal) {
        return HttpClient.put<GitHubAuditConfigResponse>(`${BASE_PATH}/config/${configId}`, config, {
            signal
        })
    },

    /**
     * Delete a GitHub Audit configuration
     */
    deleteConfig(configId: number, signal?: AbortSignal) {
        return HttpClient.delete<DeleteResponse>(`${BASE_PATH}/config/${configId}`, { signal })
    },

    // ==================== Audit Execution Endpoints ====================

    /**
     * Run a GitHub audit using a saved configuration
     */
    runAuditFromConfig(configId: number, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditResponse>(`${BASE_PATH}/config/${configId}/audit`, {}, { signal })
    },

    /**
     * Run a one-time GitHub audit without saving config
     */
    runAuditAdhoc(request: GitHubAuditRequest, githubToken: string, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditResponse>(`${BASE_PATH}/audit`, request, {
            params: { github_token: githubToken },
            signal
        })
    },

    /**
     * Run a GitHub audit from config and return summary only
     */
    runAuditSummaryFromConfig(configId: number, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditSummaryResponse>(
            `${BASE_PATH}/config/${configId}/audit/summary`,
            {},
            { signal }
        )
    },

    // ==================== Report Endpoints ====================

    /**
     * Get list of GitHub audit reports with optional filters
     */
    getReports(
        options?: {
            customerCode?: string
            configId?: number
            organization?: string
            status?: string
            limit?: number
            offset?: number
        },
        signal?: AbortSignal
    ) {
        const params: Record<string, string | number> = {}
        if (options?.customerCode) params.customer_code = options.customerCode
        if (options?.configId) params.config_id = options.configId
        if (options?.organization) params.organization = options.organization
        if (options?.status) params.status = options.status
        if (options?.limit) params.limit = options.limit
        if (options?.offset) params.offset = options.offset

        return HttpClient.get<GitHubAuditReportListResponse>(`${BASE_PATH}/reports`, {
            params,
            signal
        })
    },

    /**
     * Get a specific GitHub audit report with full details
     */
    getReport(reportId: number, signal?: AbortSignal) {
        return HttpClient.get<GitHubAuditReportResponse>(`${BASE_PATH}/reports/${reportId}`, {
            signal
        })
    },

    /**
     * Delete a GitHub audit report
     */
    deleteReport(reportId: number, signal?: AbortSignal) {
        return HttpClient.delete<DeleteResponse>(`${BASE_PATH}/reports/${reportId}`, { signal })
    },

    // ==================== Exclusion Endpoints ====================

    /**
     * Create an exclusion rule for a specific check
     */
    createExclusion(configId: number, exclusion: GitHubAuditExclusionCreate, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditExclusionResponse>(
            `${BASE_PATH}/config/${configId}/exclusions`,
            exclusion,
            { signal }
        )
    },

    /**
     * Get all exclusion rules for a configuration
     */
    getExclusions(configId: number, includeExpired?: boolean, signal?: AbortSignal) {
        const params = includeExpired !== undefined ? { include_expired: includeExpired } : undefined
        return HttpClient.get<GitHubAuditExclusionResponse>(
            `${BASE_PATH}/config/${configId}/exclusions`,
            { params, signal }
        )
    },

    /**
     * Update an exclusion rule
     */
    updateExclusion(
        exclusionId: number,
        exclusion: GitHubAuditExclusionUpdate,
        signal?: AbortSignal
    ) {
        return HttpClient.put<GitHubAuditExclusionResponse>(
            `${BASE_PATH}/exclusions/${exclusionId}`,
            exclusion,
            { signal }
        )
    },

    /**
     * Delete an exclusion rule
     */
    deleteExclusion(exclusionId: number, signal?: AbortSignal) {
        return HttpClient.delete<DeleteResponse>(`${BASE_PATH}/exclusions/${exclusionId}`, {
            signal
        })
    },

    // ==================== Baseline Endpoints ====================

    /**
     * Create a baseline from a previous audit report
     */
    createBaseline(configId: number, baseline: GitHubAuditBaselineCreate, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditBaselineResponse>(
            `${BASE_PATH}/config/${configId}/baselines`,
            baseline,
            { signal }
        )
    },

    /**
     * Get all baselines for a configuration
     */
    getBaselines(configId: number, activeOnly?: boolean, signal?: AbortSignal) {
        const params = activeOnly !== undefined ? { active_only: activeOnly } : undefined
        return HttpClient.get<GitHubAuditBaselineResponse>(
            `${BASE_PATH}/config/${configId}/baselines`,
            { params, signal }
        )
    },

    /**
     * Delete a baseline
     */
    deleteBaseline(baselineId: number, signal?: AbortSignal) {
        return HttpClient.delete<DeleteResponse>(`${BASE_PATH}/baselines/${baselineId}`, { signal })
    },

    // ==================== Reference Endpoints ====================

    /**
     * Get list of all available audit checks
     */
    getAvailableChecks(signal?: AbortSignal) {
        return HttpClient.get<AvailableChecksResponse>(`${BASE_PATH}/checks`, { signal })
    }
}
