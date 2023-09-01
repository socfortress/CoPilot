import { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "./httpClient"
import { Agents, AgentVulnerabilities, OutdatedWazuhAgents, OutdatedVelociraptorAgents } from "@/types/agents" // Import the new types

export default {
    getAgents() {
        return HttpClient.get<FlaskBaseResponse & { agents: Agents[] }>("/agents")
    },
    getAgent(id: string) {
        return HttpClient.get<FlaskBaseResponse & { agent: Agents }>(`/agents/${id}`) // Should be Agents, not Agents[]
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
        return HttpClient.get<FlaskBaseResponse & { vulnerabilities: AgentVulnerabilities[] }>(`/agents/${id}/vulnerabilities`) // Include the vulnerabilities
    },
    agentsWazuhOutdated() {
        return HttpClient.get<FlaskBaseResponse & { outdated_wazuh_agents: OutdatedWazuhAgents }>(`/agents/wazuh/outdated`) // Include the outdated Wazuh agents
    },
    agentsVelociraptorOutdated() {
        return HttpClient.get<FlaskBaseResponse & { outdated_velociraptor_agents: OutdatedVelociraptorAgents }>(
            `/agents/velociraptor/outdated`
        ) // Include the outdated Velociraptor agents
    }
}
