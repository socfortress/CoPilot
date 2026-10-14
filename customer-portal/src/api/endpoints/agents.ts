import type {
	Agent,
	AgentScaCheck,
	AgentScaPolicy,
	AgentsPageQuery,
	AgentsPageResponse,
	AgentVulnerability,
	VulnerabilitySeverity
} from "@/types/agents"
import type { Case } from "@/types/cases"
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
			withCustomerCodes(query.customerCodes, { params: agentsParams(query), responseType: "blob", keepOnNavigation: true })
		)
	},

	/**
	 * Get a specific agent by ID
	 */
	getAgentById(agentId: string) {
		return HttpClient.get<CommonResponse<{ agents: Agent[] }>>(`/agents/${agentId}`)
	},

	/** The vulnerabilities Wazuh found on the agent: every severity, filtered on the page. */
	getVulnerabilities(agentId: string, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<{ vulnerabilities: AgentVulnerability[] | null }>>(
			`/agents/${encodeURIComponent(agentId)}/vulnerabilities/All`,
			{ signal }
		)
	},

	/** The vulnerabilities of one severity (or all of them) as a CSV file, with EPSS scores where known. */
	exportVulnerabilities(agentId: string, severity: VulnerabilitySeverity | "All") {
		return HttpClient.get<Blob>(`/agents/${encodeURIComponent(agentId)}/csv/vulnerabilities/${severity}`, {
			responseType: "blob",
			keepOnNavigation: true
		})
	},

	/** The agent's SCA policies, each with its latest score. */
	getScaPolicies(agentId: string, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<{ sca: AgentScaPolicy[] | null }>>(
			`/agents/${encodeURIComponent(agentId)}/sca`,
			{ signal }
		)
	},

	/** Every check of one SCA policy on the agent. */
	getScaChecks(agentId: string, policyId: string, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<{ sca_policy_results: AgentScaCheck[] | null }>>(
			`/agents/${encodeURIComponent(agentId)}/sca/${encodeURIComponent(policyId)}`,
			{ signal }
		)
	},

	/** One SCA policy's checks as a CSV file. */
	exportScaChecks(agentId: string, policyId: string) {
		return HttpClient.get<Blob>(
			`/agents/${encodeURIComponent(agentId)}/csv/sca/${encodeURIComponent(policyId)}`,
			{ responseType: "blob", keepOnNavigation: true }
		)
	},

	/** The cases with an alert on this host, of the agent's own customer only. */
	getCases(hostname: string, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<{ cases: Case[] }>>(`/agents/${encodeURIComponent(hostname)}/cases`, {
			signal
		})
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
