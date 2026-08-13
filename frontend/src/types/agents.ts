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
	status: string
	title: string
	type: string
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

export type OutdatedWazuhAgents = Agent[]

export type OutdatedVelociraptorAgents = Agent[]

export interface AgentSca {
	// only policy_id is guaranteed — Wazuh omits the rest on some policies
	policy_id: string
	description: string | null
	fail: number
	start_scan: Date | null
	references: string | null
	name: string | null
	pass: number
	score: number
	end_scan: Date | null
	total_checks: number
	hash_file: string | null
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

export interface AgentArtifactData {
	id: number
	agent_id: string
	velociraptor_id: string
	customer_code: string | null
	artifact_name: string
	flow_id: string
	bucket_name: string
	object_key: string
	file_name: string
	content_type: string
	file_size: number
	file_hash: string
	collection_time: string
	uploaded_by: number | null
	notes: string | null
	status: string
}

// Bulk Delete Types
export type BulkDeleteAgentStatus = "disconnected" | "never_connected" | "active"

export interface BulkDeleteAgentRequest {
	agent_ids: string[]
}

export interface BulkDeleteFilterRequest {
	customer_code?: string
	status?: BulkDeleteAgentStatus
	disconnected_days?: number
}

export interface BulkDeleteAgentResult {
	agent_id: string
	success: boolean
	message: string
}

export interface BulkDeleteAgentsResponse {
	total_requested: number
	successful_deletions: number
	failed_deletions: number
	results: BulkDeleteAgentResult[]
}
