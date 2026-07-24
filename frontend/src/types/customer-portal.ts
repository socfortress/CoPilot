export interface CustomerPortalSettings {
	id: number
	title: string
	logo_base64: string
	logo_mime_type: string
	brand_color: string | null
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
	updated_at: string
	updated_by: number | null
}

/** The branding that actually resolves for a customer: override fields over global defaults. */
export interface CustomerPortalEffectiveBranding {
	title: string
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
	source: "custom" | "global"
	customer_code: string | null
}

export interface CustomerPortalBrandingListItem {
	customer_code: string
	enabled: boolean
	title: string | null
	has_logo: boolean
	brand_color: string | null
	updated_at: string
}
