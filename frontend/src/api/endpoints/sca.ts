import type {
    ScaOverviewQuery,
    ScaOverviewResponse,
    SCAReportDeleteResponse,
    SCAReportGenerateRequest,
    SCAReportGenerateResponse,
    SCAReportListResponse,
    ScaStatsResponse
} from "@/types/sca.d"
import { fetchEventSource } from "@microsoft/fetch-event-source"
import { HttpClient } from "../httpClient"
import { useAuthStore } from "@/stores/auth"

export default {
    /**
     * Search SCA results across all agents with filtering and pagination
     */
    searchScaOverview(query?: ScaOverviewQuery, signal?: AbortSignal) {
        return HttpClient.get<ScaOverviewResponse>(`/sca/overview`, {
            params: {
                customer_code: query?.customer_code,
                agent_name: query?.agent_name,
                policy_id: query?.policy_id,
                policy_name: query?.policy_name,
                min_score: query?.min_score,
                max_score: query?.max_score,
                page: query?.page || 1,
                page_size: query?.page_size || 50
            },
            signal
        })
    },

	/**
     * Stream SCA results using fetch-event-source (supports Authorization header)
     */
    async streamScaOverview(
        query: ScaOverviewQuery | undefined,
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
        const authStore = useAuthStore()

        const params = new URLSearchParams()
        if (query?.customer_code) params.append("customer_code", query.customer_code)
        if (query?.agent_name) params.append("agent_name", query.agent_name)
        if (query?.policy_id) params.append("policy_id", query.policy_id)
        if (query?.policy_name) params.append("policy_name", query.policy_name)
        if (query?.min_score !== undefined) params.append("min_score", query.min_score.toString())
        if (query?.max_score !== undefined) params.append("max_score", query.max_score.toString())

        const queryString = params.toString()
        const url = `/api/sca/overview/stream${queryString ? `?${queryString}` : ""}`

        await fetchEventSource(url, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${authStore.accessToken}`,  // Adjust based on your store
                "Accept": "text/event-stream"
            },
            signal: abortController?.signal,
            onopen(response) {
                if (response.ok) {
                    return Promise.resolve()
                }
                throw new Error(`Failed to connect: ${response.status} ${response.statusText}`)
            },
            onmessage(event) {
                if (!event.data) return

                try {
                    const data = JSON.parse(event.data)
                    switch (event.event) {
                        case "start":
                            handlers.onStart?.(data)
                            break
                        case "agent_result":
                            handlers.onAgentResult?.(data)
                            break
                        case "agent_empty":
                            handlers.onAgentEmpty?.(data)
                            break
                        case "progress":
                            handlers.onProgress?.(data)
                            break
                        case "complete":
                            handlers.onComplete?.(data)
                            break
                        case "error":
                        case "agent_error":
                            handlers.onError?.(data)
                            break
                    }
                } catch (e) {
                    console.error("Failed to parse SSE data:", e)
                }
            },
            onerror(err) {
                handlers.onError?.(err)
                throw err  // Rethrow to stop retrying
            }
        })
    },

    /**
     * Get SCA statistics
     */
    getScaStats(customer_code?: string) {
        return HttpClient.get<ScaStatsResponse>(`/sca/stats`, {
            params: customer_code ? { customer_code } : undefined
        })
    },

    /**
     * Generate an SCA report (synchronous)
     */
    generateReport(request: SCAReportGenerateRequest) {
        return HttpClient.post<SCAReportGenerateResponse>(`/sca/reports/generate`, request)
    },

    /**
     * List all SCA reports
     */
    listReports(customer_code?: string) {
        return HttpClient.get<SCAReportListResponse>(`/sca/reports`, {
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
        return HttpClient.delete<SCAReportDeleteResponse>(`/sca/reports/${reportId}`)
    }
}
