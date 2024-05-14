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
	wazuh_agent_status: AgentStatus
	velociraptor_agent_version: string
	customer_code: null | string
	vulnerabilities?: AgentVulnerabilities[]
	online?: boolean
	quarantined?: boolean
}

export enum AgentStatus {
	Active = "active",
	Disconnected = "disconnected",
	NotFound = "not found"
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

export interface AgentSca {
	description: string
	fail: number
	start_scan: Date
	references: string
	name: string
	pass: number
	score: number
	end_scan: Date
	policy_id: string
	total_checks: number
	hash_file: string
	invalid: number
}

export interface ScaPolicyResult {
	description: string
	id: number
	reason: string
	command: string
	rationale: string
	condition: "all" | "any" | "none"
	title: string
	result: "failed" | "not applicable" | "passed"
	policy_id: string
	remediation: string
	compliance: ScaPolicyResultCompliance[]
	rules: ScaPolicyResultRule[]
}

export interface ScaPolicyResultCompliance {
	value: string
	key: string
}

export interface ScaPolicyResultRule {
	type: "command" | "directory" | "file" | "numeric" | string
	rule: string
}
