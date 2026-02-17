// TODO: refactor
export interface CVSSInfo {
	base: number | null
	vector: string | null
}

export interface EPSSInfo {
	score: number | null
	percentile: number | null
	date: string | null
}

export interface KEVInfo {
	in_kev: boolean
	date_added: string | null
	due_date: string | null
	required_action: string | null
	known_ransomware_campaign_use: string | null
	vendor_project: string | null
	product: string | null
	vulnerability_name: string | null
	short_description: string | null
	notes: string | null
}

export interface AffectedProduct {
	product: string
	family: ProductFamily
	component_hint: string | null
}

export interface RemediationInfo {
	kbs: string[]
}

export interface PrioritizationInfo {
	priority: PriorityLevel
	reason: string[]
	suggested_sla: string
}

export interface SourceInfo {
	msrc_cvrf_id: string
	msrc_cvrf_url: string
	cisa_kev_url: string
}

export interface PatchTuesdayItem {
	cycle: string
	release_type: string
	cve: string
	title: string | null
	severity: string | null
	cvss: CVSSInfo
	epss: EPSSInfo
	kev: KEVInfo
	affected: AffectedProduct
	remediation: RemediationInfo
	prioritization: PrioritizationInfo
	source: SourceInfo
	timestamp_utc: string
}

export interface PriorityCounts {
	P0: number
	P1: number
	P2: number
	P3: number
}

export interface PatchTuesdaySummary {
	cycle: string
	patch_tuesday_date: string
	generated_utc: string
	unique_cves: number
	total_records: number
	by_priority: PriorityCounts
	by_family: Record<string, number>
	by_severity: Record<string, number>
}

export interface PatchTuesdayResponse {
	success: boolean
	message: string
	summary: PatchTuesdaySummary | null
	items: PatchTuesdayItem[]
}

export interface PatchTuesdaySummaryResponse {
	success: boolean
	message: string
	summary: PatchTuesdaySummary | null
	top_items: PatchTuesdayItem[]
}

export interface AvailableCyclesResponse {
	success: boolean
	message: string
	cycles: string[]
	current_cycle: string
	next_patch_tuesday: string
}

export interface PatchTuesdayQuery {
	cycle?: string
	include_epss?: boolean
	include_kev?: boolean
}

export interface PatchTuesdaySummaryQuery extends PatchTuesdayQuery {
	top_n?: number
}

export interface PatchTuesdaySearchQuery {
	cve_ids: string[]
	cycle?: string
}

export interface PatchTuesdayPriorityQuery extends PatchTuesdayQuery {
	priority_level: PriorityLevel
}

export enum PriorityLevel {
	P0 = "P0",
	P1 = "P1",
	P2 = "P2",
	P3 = "P3"
}

export enum ProductFamily {
	Windows = "Windows",
	WindowsServer = "Windows Server",
	OfficeM365 = "Office/M365",
	Exchange = "Exchange",
	SharePoint = "SharePoint",
	SQLServer = "SQL Server",
	DeveloperPlatform = "Developer Platform",
	Edge = "Edge",
	Azure = "Azure",
	Dynamics = "Dynamics",
	Other = "Other"
}

export enum MicrosoftSeverity {
	Critical = "Critical",
	Important = "Important",
	Moderate = "Moderate",
	Low = "Low"
}
