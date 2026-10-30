/**
 * Threat Intel enrichment of the customer's own IOCs (#1318): what VirusTotal and OpenCTI said
 * about an IOC of one of the user's alerts, as the backend projects it. Times are ISO 8601, UTC.
 */

export type IocSource = "virustotal" | "opencti"

/**
 * found / not_found: the source's answer (kept by the SOC for a while). not_checked: never asked.
 * unsupported: the source can't look up this kind of value. internal: a private address or name,
 * never sent. not_configured: the source is not available. error: this check failed.
 */
export type IocSourceStatus =
	| "found"
	| "not_found"
	| "not_checked"
	| "unsupported"
	| "internal"
	| "not_configured"
	| "error"

export type IocVerdict = "malicious" | "suspicious" | "known" | "clean" | "unknown"
export type IocOverallVerdict = IocVerdict | "not_found"
export type IocLookupFailure = "rate_limited" | "unavailable"
export type IocKind = "ip" | "domain" | "url" | "hash" | "other" | "internal" | "invalid"

export interface VirusTotalDetails {
	malicious: number
	suspicious: number
	harmless: number
	undetected: number
	engines: number
	reputation: number | null
	last_analysis_at: string | null
	tags: string[]
	country: string | null
	as_owner: string | null
	type_description: string | null
	link: string | null
}

export interface OpenCtiIndicator {
	name: string | null
	score: number | null
	valid_until: string | null
	revoked: boolean
}

export interface OpenCtiReport {
	name: string
	published: string | null
}

export interface OpenCtiDetails {
	score: number | null
	entity_types: string[]
	labels: string[]
	indicators: OpenCtiIndicator[]
	reports: OpenCtiReport[]
	/** Indicators and reports left out because their sharing marking does not allow it. */
	withheld: number
}

export interface IocSourceResult {
	source: IocSource
	status: IocSourceStatus
	verdict: IocVerdict | null
	checked_at: string | null
	error: IocLookupFailure | null
	virustotal: VirusTotalDetails | null
	opencti: OpenCtiDetails | null
}

export interface IocEnrichment {
	ioc_id: number
	value: string
	type: string | null
	kind: IocKind
	verdict: IocOverallVerdict | null
	checked_at: string | null
	/** A source can be asked now: never asked, or its answer is older than the SOC keeps it. */
	can_check: boolean
	/** When the answers shown can be refreshed. */
	next_check_at: string | null
	sources: IocSourceResult[]
}

export interface AlertIocEnrichment {
	alert_id: number
	iocs: IocEnrichment[]
	sources: IocSource[]
}

export interface IocEnrichmentAvailability {
	customer_code: string | null
	enabled: boolean
	sources: IocSource[]
}
