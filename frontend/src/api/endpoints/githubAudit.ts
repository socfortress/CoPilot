import type {
    GitHubAuditRequest,
    GitHubAuditResponse,
    GitHubAuditSummaryResponse
} from "@/types/githubAudit.d"
import { HttpClient } from "../httpClient"

const BASE_PATH = "/github-audit"

export default {
    /**
     * Run a full GitHub organization security audit
     */
    runAudit(request: GitHubAuditRequest, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditResponse>(`${BASE_PATH}/audit`, request, { signal })
    },

    /**
     * Run a GitHub audit and return summary only (lighter endpoint)
     */
    runAuditSummary(request: GitHubAuditRequest, signal?: AbortSignal) {
        return HttpClient.post<GitHubAuditSummaryResponse>(`${BASE_PATH}/audit/summary`, request, {
            signal
        })
    },

    /**
     * Get list of all available audit checks
     */
    getAvailableChecks(signal?: AbortSignal) {
        return HttpClient.get<{
            success: boolean
            checks: Array<{
                id: string
                name: string
                category: string
                severity: string
            }>
        }>(`${BASE_PATH}/checks`, { signal })
    }
}
