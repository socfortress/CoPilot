import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type {
	Agent,
	AgentVulnerabilities,
	OutdatedWazuhAgents,
	OutdatedVelociraptorAgents,
	AgentSca,
	ScaPolicyResult
} from "@/types/agents.d"

export interface AgentPayload {
	velociraptor_id: string
}

export type VulnerabilitySeverityType = "Low" | "Medium" | "High" | "Critical"

export default {
	getAgents(agentId?: string) {
		return HttpClient.get<FlaskBaseResponse & { agents: Agent[] }>(`/agents${agentId ? "/" + agentId : ""}`)
	},
	markCritical(agentId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/agents/${agentId}/critical`)
	},
	markNonCritical(agentId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/agents/${agentId}/noncritical`)
	},
	deleteAgent(agentId: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/agents/${agentId}/delete`)
	},
	syncAgents() {
		return HttpClient.post<FlaskBaseResponse>(`/agents/sync`)
	},
	agentVulnerabilities(agentId: string, severity: VulnerabilitySeverityType) {
		return HttpClient.get<FlaskBaseResponse & { vulnerabilities: AgentVulnerabilities[] }>(
			`/agents/${agentId}/vulnerabilities/${severity}`
		)
	},
	getSocCases(agentId: string | number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { case_ids: number[] }>(
			`/agents/${agentId}/soc_cases`,
			signal ? { signal } : {}
		)
	},
	getSCA(agentId: string | number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { sca: AgentSca[] }>(
			`/agents/${agentId}/sca`,
			signal ? { signal } : {}
		)
	},
	getSCAResults(agentId: string | number, policyId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { sca_policy_results: ScaPolicyResult[] }>(
			`/agents/${agentId}/sca/${policyId}`,
			signal ? { signal } : {}
		)
	},
	updateAgent(agentId: string, payload: AgentPayload) {
		return HttpClient.put<FlaskBaseResponse>(
			`/agents/${agentId}/update`,
			{},
			{
				params: {
					velociraptor_id: payload.velociraptor_id
				}
			}
		)
	},
	upgradeWazuhAgent(agentId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/agents/${agentId}/wazuh/upgrade`)
	},

	// IGNORE AT THE MOMENT !
	agentsWazuhOutdated() {
		return HttpClient.get<FlaskBaseResponse & { outdated_wazuh_agents: OutdatedWazuhAgents }>(
			`/agents/wazuh/outdated`
		) // Include the outdated Wazuh agents
	},
	// IGNORE AT THE MOMENT !
	agentsVelociraptorOutdated() {
		return HttpClient.get<FlaskBaseResponse & { outdated_velociraptor_agents: OutdatedVelociraptorAgents }>(
			`/agents/velociraptor/outdated`
		) // Include the outdated Velociraptor agents
	}
}
