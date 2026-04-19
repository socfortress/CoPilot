import type { Agent } from "@/types/agents"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"

export default {
	/**
	 * Get all agents for the authenticated customer
	 */
	getAgents() {
		return HttpClient.get<CommonResponse<{ agents: Agent[] }>>("/agents")
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
