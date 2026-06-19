import type { VulnerabilitySearchQuery } from "@/types/vulnerabilities"

export type VulnerabilitiesFilterTypes = keyof Omit<VulnerabilitySearchQuery, "page" | "page_size" | "include_epss">

export interface VulnerabilitiesListFilter {
	type: VulnerabilitiesFilterTypes
	value: string | null
}

export interface VulnerabilitySeverityCounts {
	critical: number
	high: number
	medium: number
	low: number
}

export interface VulnerabilityCoverageCounts {
	uniqueAgents: number
	uniquePackages: number
	uniqueCustomers: number
}

export interface VulnerabilityTopEpssPackage {
	package_name: string
	vulnCount: number
	maxEpssScore: number
	maxCvssScore: number | null
	affectedAgents: number
	criticalCount: number
	highCount: number
}
