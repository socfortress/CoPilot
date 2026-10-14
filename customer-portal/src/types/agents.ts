export type AgentStatus = "active" | "disconnected" | "never_connected" | "pending"

export interface Agent {
	id: number
	agent_id: string
	ip_address: string
	os: string
	hostname: string
	label: string
	critical_asset: boolean
	quarantined: boolean
	wazuh_last_seen: Date
	wazuh_agent_version: string
	wazuh_agent_status: AgentStatus
	velociraptor_id: string | null
	velociraptor_agent_version: string | null
	velociraptor_last_seen: Date | null
	velociraptor_org: string | null
	customer_code: string
}

/** Counts over every agent in scope, independent of the list filters. */
export interface AgentsStats {
	total: number
	active: number
	critical: number
	offline: number
}

export interface AgentsPageQuery {
	page: number
	pageSize: number
	search?: string | null
	status?: string | null
	os?: string | null
	critical?: boolean
	customerCodes?: string[]
}

/** `GET /customer_portal/agents`: one page, the filtered total, the cards and the filter options. */
export interface AgentsPageResponse {
	agents: Agent[]
	total: number
	stats: AgentsStats
	statuses: AgentStatus[]
	os_list: string[]
}

/** Severities the vulnerability endpoints filter on; `All` is every one of them. */
export type VulnerabilitySeverity = "Critical" | "High" | "Medium" | "Low"

/** One vulnerability Wazuh found on an agent (`GET /agents/{id}/vulnerabilities/{severity}`). */
export interface AgentVulnerability {
	cve: string | null
	severity: string | null
	title: string | null
	name: string | null
	version: string | null
	type: string | null
	architecture: string | null
	status: string | null
	cvss3_score: number | null
	published: string | null
	detection_time: string | null
	external_references: string[] | null
}

/** An SCA policy's latest scan on an agent (`GET /agents/{id}/sca`). Wazuh omits fields on some policies. */
export interface AgentScaPolicy {
	policy_id: string
	name: string | null
	description: string | null
	references: string | null
	pass: number
	fail: number
	invalid: number
	score: number
	total_checks: number
	start_scan: string | null
	end_scan: string | null
}

export type AgentScaCheckResult = "passed" | "failed" | "not applicable"

/** One check of an SCA policy (`GET /agents/{id}/sca/{policy_id}`). */
export interface AgentScaCheck {
	id: number
	policy_id: string
	title: string
	description: string | null
	rationale: string | null
	remediation: string | null
	reason: string | null
	command: string | null
	condition: string | null
	result: AgentScaCheckResult | string
	compliance: { key: string; value: string }[]
	rules: { type: string; rule: string }[]
}
