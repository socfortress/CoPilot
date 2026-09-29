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
