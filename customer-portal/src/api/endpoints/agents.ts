import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"

export interface Agent {
	id: number
	agent_id: string
	ip_address: string
	os: string
	hostname: string
	label: string
	critical_asset: boolean
	wazuh_last_seen: string
	velociraptor_id: string | null
	velociraptor_last_seen: string | null
	wazuh_agent_version: string
	wazuh_agent_status: string
	velociraptor_agent_version: string | null
	customer_code: string
	quarantined: boolean
	velociraptor_org: string | null
}

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
		return HttpClient.get<CommonResponse<{ agent: Agent }>>(`/agents/${agentId}`)
	},

	/**
	 * Get agent by hostname
	 */
	getAgentByHostname(hostname: string) {
		return HttpClient.get<CommonResponse<{ agent: Agent }>>(`/agents/hostname/${hostname}`)
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
