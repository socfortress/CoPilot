import type { VulnerabilitySearchQuery } from "@/types/vulnerabilities.d"

export type VulnerabilitiesFilterTypes = keyof Omit<VulnerabilitySearchQuery, "page" | "page_size" | "include_epss">

export interface VulnerabilitiesListFilter {
	type: VulnerabilitiesFilterTypes
	value: string | null
}
