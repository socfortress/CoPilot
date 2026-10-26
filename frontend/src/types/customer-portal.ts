export interface CustomerPortalSettings {
	id: number
	title: string
	logo_base64: string
	logo_mime_type: string
	brand_color: string | null
	/** The portal's interface takes `brand_color` as its primary color (#1278). Off by default. */
	theme_from_brand_color: boolean
	updated_at: Date
}

/** A customer's stored branding override, exactly as configured (no global fallback applied). */
export interface CustomerPortalBrandingOverride {
	id: number
	customer_code: string
	enabled: boolean
	title: string | null
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
	/** Null inherits the global choice. */
	theme_from_brand_color: boolean | null
	updated_at: string
	updated_by: number | null
}

/** The branding that actually resolves for a customer: override fields over global defaults. */
export interface CustomerPortalEffectiveBranding {
	title: string
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
	theme_from_brand_color: boolean
	source: "custom" | "global"
	customer_code: string | null
}

/**
 * Per-customer switch for the portal's AI Analyst surfaces (overview insights
 * card + alert-detail AI Report tab). Opt-in: a customer with no stored row
 * comes back as `enabled: false`.
 */
export interface CustomerPortalAiReportSettings {
	customer_code: string
	enabled: boolean
	/** Portal users may ask for an analysis of an alert (#1215); only effective with `enabled`. */
	allow_customer_requests: boolean
	/** Portal requests allowed in any 24 hours; null = unlimited. Never shown to the customer. */
	daily_request_limit: number | null
	/** Portal requests made in the last 24 hours, for the operator. */
	requests_last_24h: number
	updated_at: string | null
	updated_by: number | null
}

/**
 * Per-customer switch for portal users' email and in-app notifications (#1282). Opt-in:
 * a missing row reads as off. Each portal user then picks what they get.
 */
export interface CustomerPortalNotificationSettings {
	customer_code: string
	enabled: boolean
	updated_at: string | null
	updated_by: number | null
}

/** Per-customer switch for the Customer Portal's SLA page (#1187). Opt-in: a missing row reads as off. */
export interface CustomerPortalSlaSettings {
	customer_code: string
	enabled: boolean
	updated_at: string | null
	updated_by: number | null
}

/** Per-customer switch for the Customer Portal's Activity page (#1284). Opt-in: a missing row reads as off. */
export interface CustomerPortalActivitySettings {
	customer_code: string
	enabled: boolean
	updated_at: string | null
	updated_by: number | null
}

/** Per-customer switch for the Customer Portal's Exposure page (#1289). Opt-in: a missing row reads as off. */
export interface CustomerPortalExposureSettings {
	customer_code: string
	enabled: boolean
	updated_at: string | null
	updated_by: number | null
}

/**
 * Per-customer switch for the Customer Portal's Audit Log page (#1298): the customer's own administrators
 * read who did what in their tenant. Opt-in: a missing row reads as off.
 */
export interface CustomerPortalAuditSettings {
	customer_code: string
	enabled: boolean
	updated_at: string | null
	updated_by: number | null
}

/**
 * The languages a customer's portal users may pick (#1310). English is always among them and is the
 * default; a missing row reads as English only.
 */
export interface CustomerPortalLanguageSettings {
	customer_code: string
	/** English first, then the others in the portal's order. */
	languages: string[]
	updated_at: string | null
	updated_by: number | null
}

export interface CustomerPortalBrandingListItem {
	customer_code: string
	enabled: boolean
	title: string | null
	has_logo: boolean
	brand_color: string | null
	theme_from_brand_color: boolean | null
	updated_at: string
}
