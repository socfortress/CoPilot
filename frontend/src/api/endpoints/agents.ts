import type {
	Agent,
    AgentArtifactData,
	AgentSca,
	AgentVulnerabilities,
	OutdatedVelociraptorAgents,
	OutdatedWazuhAgents,
	ScaPolicyResult
} from "@/types/agents.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface AgentPayload {
	velociraptor_id: string
}

export type VulnerabilitySeverityType = "Low" | "Medium" | "High" | "Critical" | "All"

export interface AgentDataStoreListResponse extends FlaskBaseResponse {
    data: AgentArtifactData[]
    total: number
}

export interface AgentDataStoreResponse extends FlaskBaseResponse {
    data: AgentArtifactData | null
}

export default {
	getAgents(agentId?: string) {
		return HttpClient.get<FlaskBaseResponse & { agents: Agent[] }>(`/agents${agentId ? `/${agentId}` : ""}`)
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
	syncVulnerabilities(customerCode: string) {
		return HttpClient.post<FlaskBaseResponse>(`/agents/sync/vulnerabilities/${customerCode}`)
	},
	agentVulnerabilities(agentId: string, severity: VulnerabilitySeverityType, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { vulnerabilities: AgentVulnerabilities[] }>(
			`/agents/${agentId}/vulnerabilities/${severity}`,
			signal ? { signal } : {}
		)
	},
	agentVulnerabilitiesDownload(agentId: string, severity: VulnerabilitySeverityType) {
		return HttpClient.get<string>(`/agents/${agentId}/csv/vulnerabilities/${severity}`)
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
	scaResultsDownload(agentId: string | number, policyId: string) {
		return HttpClient.get<Blob>(`/agents/${agentId}/csv/sca/${policyId}`, {
			responseType: "blob"
		})
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
    // Agent Data Store / Artifact Collection Methods
    /**
     * List all artifact files for a specific agent
     * @param agentId - The agent ID
     * @param flowId - Optional flow ID to filter artifacts
     * @param signal - Optional AbortSignal for request cancellation
     */
    listAgentArtifacts(agentId: string, flowId?: string, signal?: AbortSignal) {
        const params = flowId ? { flow_id: flowId } : {}
        return HttpClient.get<AgentDataStoreListResponse>(
            `/agent_data_store/agent/${agentId}/artifacts`,
            signal ? { signal, params } : { params }
        )
    },

    /**
     * Get details of a specific artifact file
     * @param agentId - The agent ID
     * @param artifactId - The artifact ID
     * @param signal - Optional AbortSignal for request cancellation
     */
    getAgentArtifactDetails(agentId: string, artifactId: number, signal?: AbortSignal) {
        return HttpClient.get<AgentDataStoreResponse>(
            `/agent_data_store/agent/${agentId}/artifacts/${artifactId}`,
            signal ? { signal } : {}
        )
    },

    /**
     * Download a specific artifact file
     * @param agentId - The agent ID
     * @param artifactId - The artifact ID
     * @returns Promise with Blob response
     */
    downloadAgentArtifact(agentId: string, artifactId: number) {
        return HttpClient.get<Blob>(`/agent_data_store/agent/${agentId}/artifacts/${artifactId}/download`, {
            responseType: "blob"
        })
    },

    /**
     * Delete a specific artifact file
     * @param agentId - The agent ID
     * @param artifactId - The artifact ID
     */
    deleteAgentArtifact(agentId: string, artifactId: number) {
        return HttpClient.delete<FlaskBaseResponse>(`/agent_data_store/agent/${agentId}/artifacts/${artifactId}`)
    },

	// IGNORE AT THE MOMENT !
	/** @deprecated */
	agentsWazuhOutdated() {
		return HttpClient.get<FlaskBaseResponse & { outdated_wazuh_agents: OutdatedWazuhAgents }>(
			`/agents/wazuh/outdated`
		) // Include the outdated Wazuh agents
	},
	// IGNORE AT THE MOMENT !
	/** @deprecated */
	agentsVelociraptorOutdated() {
		return HttpClient.get<FlaskBaseResponse & { outdated_velociraptor_agents: OutdatedVelociraptorAgents }>(
			`/agents/velociraptor/outdated`
		) // Include the outdated Velociraptor agents
	}
}
