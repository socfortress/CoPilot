export interface VulnerabilitySearchItem {
	cve_id: string
	severity: VulnerabilitySeverity
	title: string
	agent_name: string
	customer_code?: string | null
	references?: string | null
	detected_at: string
	published_at?: string | null
	base_score?: number | null
	package_name?: string | null
	package_version?: string | null
	package_architecture?: string | null
	epss_score?: string | null
	epss_percentile?: string | null
}

export interface VulnerabilitySearchResponse {
	vulnerabilities: VulnerabilitySearchItem[]
	total_count: number
	critical_count: number
	high_count: number
	medium_count: number
	low_count: number
	page: number
	page_size: number
	total_pages: number
	has_next: boolean
	has_previous: boolean
	success: boolean
	message: string
	filters_applied: Record<string, any>
}

export enum VulnerabilitySeverity {
	Critical = "Critical",
	High = "High",
	Medium = "Medium",
	Low = "Low"
}

export interface VulnerabilitySearchQuery {
	customer_code?: string
	agent_name?: string
	severity?: VulnerabilitySeverity
	cve_id?: string
	package_name?: string
	page?: number
	page_size?: number
	include_epss?: boolean
}
