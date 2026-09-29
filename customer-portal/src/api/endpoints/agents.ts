import type { Agent, AgentsPageQuery, AgentsPageResponse } from "@/types/agents"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

function agentsParams(query: Partial<AgentsPageQuery>) {
	return {
		page: query.page,
		page_size: query.pageSize,
		search: query.search || undefined,
		status: query.status || undefined,
		os: query.os || undefined,
		critical: query.critical || undefined
	}
}

export default {
	/** One page of agents, filtered server-side, with the page's cards and filter options. */
	getAgentsPage(query: AgentsPageQuery, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AgentsPageResponse>>(
			"/customer_portal/agents",
			withCustomerCodes(query.customerCodes, { params: agentsParams(query), signal })
		)
	},

	/** Every agent matching the filters, as a CSV file. */
	exportAgents(query: Omit<AgentsPageQuery, "page" | "pageSize">) {
		return HttpClient.get<Blob>(
			"/customer_portal/agents/export",
			withCustomerCodes(query.customerCodes, { params: agentsParams(query), responseType: "blob" })
		)
	},

	/**
	 * Get a specific agent by ID
	 */
	getAgentById(agentId: string) {
		return HttpClient.get<CommonResponse<{ agents: Agent[] }>>(`/agents/${agentId}`)
	},

	/**
	 * Mark agent as critical
	 */
	markAgentAsCritical(agentId: string) {
		return HttpClient.post<CommonResponse>(`/agents/${agentId}/critical`)
	},

	/**
	 * Mark agent as not critical
	 */
	markAgentAsNotCritical(agentId: string) {
		return HttpClient.post<CommonResponse>(`/agents/${agentId}/noncritical`)
	}
}
