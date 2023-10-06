export interface Agent {
	id?: number
	agent_id: string
	ip_address: string
	os: string
	hostname: string
	label: string
	critical_asset: boolean
	wazuh_last_seen: string
	velociraptor_id: string
	velociraptor_last_seen: string
	wazuh_agent_version: string
	velociraptor_agent_version: string
	customer_code: null | string
	vulnerabilities?: AgentVulnerabilities[]
	online?: boolean
}

export interface AgentVulnerabilities {
	id?: string
	architecture: string
	condition: string
	cve: string
	cvss2_score: number
	cvss3_score: number
	detection_time: string
	external_references: string[]
	name: string
	published: string
	severity: VulnerabilitySeverity
	status: VulnerabilityStatus
	title: string
	type: VulnerabilityType
	updated: string
	version: string
}

export enum VulnerabilitySeverity {
	Critical = "Critical",
	High = "High",
	Low = "Low",
	Medium = "Medium",
	Untriaged = "Untriaged"
}

export enum VulnerabilityStatus {
	Valid = "VALID"
}

export enum VulnerabilityType {
	Package = "PACKAGE"
}

export type OutdatedWazuhAgents = Agent[]

export type OutdatedVelociraptorAgents = Agent[]
