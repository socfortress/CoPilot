import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { Agent, AgentVulnerabilities, OutdatedWazuhAgents, OutdatedVelociraptorAgents } from "@/types/agents.d"

export default {
	getAgents(id?: string) {
		return HttpClient.get<FlaskBaseResponse & { agents: Agent[] }>(`/agents${id ? "/" + id : ""}`)
	},
	markCritical(id: string) {
		return HttpClient.post<FlaskBaseResponse>(`/agents/${id}/critical`)
	},
	markNonCritical(id: string) {
		return HttpClient.post<FlaskBaseResponse>(`/agents/${id}/noncritical`)
	},
	deleteAgent(id: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/agents/${id}/delete`)
	},
	syncAgents() {
		return HttpClient.post<FlaskBaseResponse>(`/agents/sync`)
	},
	agentVulnerabilities(id: string) {
		return HttpClient.get<FlaskBaseResponse & { vulnerabilities: AgentVulnerabilities[] }>(
			`/agents/${id}/vulnerabilities`
		)
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
