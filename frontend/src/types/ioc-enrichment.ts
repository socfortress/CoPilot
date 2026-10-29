/**
 * Threat Intel enrichment of a customer's own IOCs in the Customer Portal (#1318): the
 * per-customer switch CoPilot's operators set under Customers → Customer → IOC Enrichment.
 */

export interface CustomerPortalIocEnrichmentSettings {
	customer_code: string
	enabled: boolean
	/** Lookups per customer over any 24 hours that reached a source; null = unlimited. */
	daily_lookup_limit: number | null
	updated_at: string | null
	updated_by: number | null
}

/** Whether each source's connector holds its credentials and is verified. */
export interface IocEnrichmentConnectors {
	virustotal: boolean
	opencti: boolean
}
