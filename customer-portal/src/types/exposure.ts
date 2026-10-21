/**
 * Vulnerabilities and compliance across a customer's agents (#1289): `/customer_portal/exposure/*`.
 *
 * Read live from Wazuh for the agents of the caller's customers whose page is on. A source
 * Wazuh could not answer for is an `error` on the response; times are ISO 8601 UTC.
 */

export type ExposureSeverity = "Critical" | "High" | "Medium" | "Low"

export interface ExposureAvailability {
	customer_code: string | null
	enabled: boolean
}

export interface SeverityCount {
	severity: ExposureSeverity
	cves: number
	hosts: number
	findings: number
}

export interface ExposureTotals {
	cves: number
	hosts: number
	findings: number
}

export interface CveRow {
	cve_id: string
	severity: string | null
	cvss: number | null
	epss: string | null
	hosts: number
	packages: string[]
	first_detected: string | null
	published: string | null
}

export interface ExposureVulnerabilities {
	enabled: boolean
	customer_codes: string[]
	agents_in_scope: number
	severities: SeverityCount[]
	totals: ExposureTotals
	cves: CveRow[]
	total_cves: number
	page: number
	page_size: number
	truncated: boolean
	error: string | null
}

export interface CveAgent {
	agent_id: string
	hostname: string
	customer_code: string
	package: string | null
	version: string | null
	detected: string | null
}

export interface CveDetail {
	cve_id: string
	severity: string | null
	cvss: number | null
	epss: string | null
	description: string | null
	references: string[]
	published: string | null
	agents: CveAgent[]
	truncated: boolean
	error: string | null
}

export interface PolicyRow {
	policy_id: string
	name: string | null
	description: string | null
	agents: number
	average_score: number
	min_score: number
	passed: number
	failed: number
	invalid: number
	agents_below: number
}

export interface ExposureCompliance {
	enabled: boolean
	customer_codes: string[]
	agents_in_scope: number
	agents_assessed: number
	unavailable_agents: number
	average_score: number | null
	passed: number
	failed: number
	weak_score: number
	policies: PolicyRow[]
	read_at: string | null
	error: string | null
}

export interface PolicyAgent {
	agent_id: string
	hostname: string
	customer_code: string
	score: number
	passed: number
	failed: number
	invalid: number
	end_scan: string | null
}

export interface PolicyAgents {
	policy_id: string
	name: string | null
	agents: PolicyAgent[]
	error: string | null
}

export interface VulnerabilityQuery {
	severity?: ExposureSeverity | null
	search?: string | null
	page?: number
	pageSize?: number
}
