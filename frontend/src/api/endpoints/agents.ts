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
	getAgents(arg?: string | GetAgentsQuery, signal?: AbortSignal) {
		// Support legacy signature getAgents(agentId?: string)
		if (typeof arg === "string") {
			return HttpClient.get<FlaskBaseResponse & { agents: Agent[] }>(
				`/agents/${arg}`,
				signal ? { signal } : undefined
			)
		}

		const agentId = arg?.agentId
		const url = `/agents${agentId ? `/${agentId}` : ""}`

		const params: Record<string, number | string | string[]> = {}
		if (arg?.customerCodes?.length) params.customer_codes = arg.customerCodes
		if (arg?.search) params.search = arg.search
		if (arg?.limit !== undefined) params.limit = arg.limit

		const requestConfig = {
			...(Object.keys(params).length ? { params, paramsSerializer: { indexes: null } } : {}),
			...(signal ? { signal } : {})
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
		agentId: string,
		cve: string,
		params?: { package?: string; version?: string },
		signal?: AbortSignal
	) {
		// dedicated single-CVE lookup — the severity list endpoint scrolls every
		// vulnerability document of the agent and takes minutes on real data
		return HttpClient.get<FlaskBaseResponse & { vulnerabilities: AgentVulnerabilities[] }>(
			`/agents/${agentId}/vulnerabilities/cve/${encodeURIComponent(cve)}`,
			{ params: params ?? {}, ...(signal ? { signal } : {}) }
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
	getSCA(agentId: string | number, policyId?: string, signal?: AbortSignal) {
		// policyId narrows the Wazuh query to one policy — the detail view must not
		// pull the agent's whole SCA list just to render a single one
		return HttpClient.get<FlaskBaseResponse & { sca: AgentSca[] }>(`/agents/${agentId}/sca`, {
			params: policyId ? { policy_id: policyId } : {},
			...(signal ? { signal } : {})
		})
	},
	getSCAResults(agentId: string | number, policyId: string, checkId?: number, signal?: AbortSignal) {
		// checkId narrows the Wazuh query to one check — the check detail view must
		// not pull the policy's whole check list just to render a single one
		return HttpClient.get<FlaskBaseResponse & { sca_policy_results: ScaPolicyResult[] }>(
			`/agents/${agentId}/sca/${policyId}`,
			{
				params: checkId != null ? { check_id: checkId } : {},
				...(signal ? { signal } : {})
			}
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
