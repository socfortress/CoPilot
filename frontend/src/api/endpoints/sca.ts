import type { ScaOverviewQuery, ScaOverviewResponse, ScaStatsResponse } from "@/types/sca.d"
import { HttpClient } from "../httpClient"

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
	 * Get SCA statistics across all agents or for a specific customer
	 */
	getScaStats(customer_code?: string, signal?: AbortSignal) {
		return HttpClient.get<ScaStatsResponse>(`/sca/stats`, {
			params: {
				customer_code
			},
			signal
		})
	}
}
