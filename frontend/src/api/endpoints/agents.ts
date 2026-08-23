import type {
	Agent,
	AgentArtifactData,
	AgentSca,
	AgentVulnerabilities,
	BulkDeleteAgentRequest,
	BulkDeleteAgentsResponse,
	BulkDeleteFilterRequest,
	OutdatedVelociraptorAgents,
	OutdatedWazuhAgents,
	ScaPolicyResult
} from "@/types/agents"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"
import { searchLimitParams } from "../params"

export interface AgentPayload {
	velociraptor_id: string
}

export interface GetAgentsQuery {
	agentId?: string
	customerCodes?: string[]
	/** Server-side substring match on hostname, label, IP, or agent id. */
	search?: string
	/** Cap the number of returned agents (used by the search palette). */
	limit?: number
}

export interface AgentArtifactsQuery {
	agentId: string
	flowId?: string
}

export type VulnerabilitySeverityType = "Low" | "Medium" | "High" | "Critical" | "All"

export default {
	getAgents(query: GetAgentsQuery, signal?: AbortSignal) {
		const url = `/agents${query.agentId ? `/${query.agentId}` : ""}`

		const params: Record<string, number | string | string[]> = {
			...(query.customerCodes?.length ? { customer_codes: query.customerCodes } : {}),
			...searchLimitParams(query)
		}

		const requestConfig = {
			...(Object.keys(params).length ? { params, paramsSerializer: { indexes: null } } : {}),
			signal
		}

		return HttpClient.get<FlaskBaseResponse & { agents: Agent[] }>(url, requestConfig)
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
	/**
	 * Bulk delete agents by their IDs
	 * @param agentIds - Array of agent IDs to delete
	 */
	bulkDeleteAgents(agentIds: string[]) {
		const payload: BulkDeleteAgentRequest = { agent_ids: agentIds }
		return HttpClient.post<FlaskBaseResponse & BulkDeleteAgentsResponse>(`/agents/bulk/delete`, payload)
	},
	/**
	 * Bulk delete agents based on filter conditions
	 * At least one filter must be specified
	 * @param filters - Filter conditions (customer_code, status, disconnected_days)
	 */
	bulkDeleteAgentsByFilter(filters: BulkDeleteFilterRequest) {
		return HttpClient.post<FlaskBaseResponse & BulkDeleteAgentsResponse>(`/agents/bulk/delete/filter`, filters)
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
	agentVulnerabilityByCve(
		query: { agentId: string; cve: string; params?: { package?: string; version?: string } },
		signal?: AbortSignal
	) {
		// dedicated single-CVE lookup — the severity list endpoint scrolls every
		// vulnerability document of the agent and takes minutes on real data
		return HttpClient.get<FlaskBaseResponse & { vulnerabilities: AgentVulnerabilities[] }>(
			`/agents/${query.agentId}/vulnerabilities/cve/${encodeURIComponent(query.cve)}`,
			{ params: query.params ?? {}, signal }
		)
	},
	agentVulnerabilitiesDownload(agentId: string, severity: VulnerabilitySeverityType, signal?: AbortSignal) {
		return HttpClient.get<string>(`/agents/${agentId}/csv/vulnerabilities/${severity}`, { signal })
	},
	getSocCases(agentId: string | number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { case_ids: number[] }>(
			`/agents/${agentId}/soc_cases`,
			signal ? { signal } : {}
		)
	},
	getSCA(query: { agentId: string | number; policyId?: string }, signal?: AbortSignal) {
		// policyId narrows the Wazuh query to one policy — the detail view must not
		// pull the agent's whole SCA list just to render a single one
		return HttpClient.get<FlaskBaseResponse & { sca: AgentSca[] }>(`/agents/${query.agentId}/sca`, {
			params: query.policyId ? { policy_id: query.policyId } : {},
			signal
		})
	},
	getSCAResults(query: { agentId: string | number; policyId: string; checkId?: number }, signal?: AbortSignal) {
		// checkId narrows the Wazuh query to one check — the check detail view must
		// not pull the policy's whole check list just to render a single one
		return HttpClient.get<FlaskBaseResponse & { sca_policy_results: ScaPolicyResult[] }>(
			`/agents/${query.agentId}/sca/${query.policyId}`,
			{
				params: query.checkId != null ? { check_id: query.checkId } : {},
				signal
			}
		)
	},
	scaResultsDownload(agentId: string | number, policyId: string, signal?: AbortSignal) {
		return HttpClient.get<Blob>(`/agents/${agentId}/csv/sca/${policyId}`, { responseType: "blob", signal })
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
	/** List all artifact files for a specific agent. */
	listAgentArtifacts(query: AgentArtifactsQuery, signal?: AbortSignal) {
		const params = query.flowId ? { flow_id: query.flowId } : {}
		return HttpClient.get<
			FlaskBaseResponse & {
				data: AgentArtifactData[]
				total: number
			}
		>(`/agent_data_store/agent/${query.agentId}/artifacts`, signal ? { signal, params } : { params })
	},

	/**
	 * Get details of a specific artifact file
	 * @param agentId - The agent ID
	 * @param artifactId - The artifact ID
	 * @param signal - Optional AbortSignal for request cancellation
	 */
	getAgentArtifactDetails(agentId: string, artifactId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { data: AgentArtifactData | null }>(
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
	downloadAgentArtifact(agentId: string, artifactId: number, signal?: AbortSignal) {
		return HttpClient.get<Blob>(`/agent_data_store/agent/${agentId}/artifacts/${artifactId}/download`, {
			responseType: "blob",
			signal
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
	agentsWazuhOutdated(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { outdated_wazuh_agents: OutdatedWazuhAgents }>(
			`/agents/wazuh/outdated`,
			{ signal }
		) // Include the outdated Wazuh agents
	},
	// IGNORE AT THE MOMENT !
	/** @deprecated */
	agentsVelociraptorOutdated(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { outdated_velociraptor_agents: OutdatedVelociraptorAgents }>(
			`/agents/velociraptor/outdated`,
			{ signal }
		) // Include the outdated Velociraptor agents
	}
}
