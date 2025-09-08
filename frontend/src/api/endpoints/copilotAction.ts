import type {
	ActionDetailResponse,
	InventoryMetricsResponse,
	InventoryResponse,
	InvokeCopilotActionRequest,
	InvokeCopilotActionResponse,
	TechnologiesResponse,
	Technology
} from "@/types/copilotAction.d"
import { HttpClient } from "../httpClient"

export interface CopilotActionInventoryQuery {
	/** Filter by technology type */
	technology?: Technology
	/** Filter by category */
	category?: string
	/** Filter by tag */
	tag?: string
	/** Free-text search query */
	q?: string
	/** Maximum number of results */
	limit?: number
	/** Offset for pagination */
	offset?: number
	/** Force refresh cache */
	refresh?: boolean
	/** Comma-separated extra fields to include */
	include?: string
}

export default {
	/**
	 * Get inventory of available active response scripts
	 */
	getInventory(query?: CopilotActionInventoryQuery, signal?: AbortSignal) {
		return HttpClient.get<InventoryResponse>(`/copilot_action/inventory`, {
			params: {
				technology: query?.technology,
				category: query?.category,
				tag: query?.tag,
				q: query?.q,
				limit: query?.limit || 100,
				offset: query?.offset || 0,
				refresh: query?.refresh || false,
				include: query?.include
			},
			signal
		})
	},

	/**
	 * Get details for a specific active response script
	 */
	getActionByName(copilotActionName: string, signal?: AbortSignal) {
		return HttpClient.get<ActionDetailResponse>(`/copilot_action/inventory/${copilotActionName}`, {
			signal
		})
	},

	/**
	 * Get inventory metrics and status
	 */
	getMetrics(signal?: AbortSignal) {
		return HttpClient.get<InventoryMetricsResponse>(`/copilot_action/metrics`, {
			signal
		})
	},

	/**
	 * Get available technology types
	 */
	getTechnologies(signal?: AbortSignal) {
		return HttpClient.get<TechnologiesResponse>(`/copilot_action/technologies`, {
			signal
		})
	},

	/**
	 * Invoke a Copilot Action on multiple target agents
	 */
	invokeAction(payload: InvokeCopilotActionRequest, signal?: AbortSignal) {
		return HttpClient.post<InvokeCopilotActionResponse>(`/copilot_action/invoke`, payload, {
			signal
		})
	}
}
