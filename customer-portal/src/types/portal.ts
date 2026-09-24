/** The global settings as served publicly: the logo is fetched separately from `logo_url`. */
export interface PortalSettings {
	id: number
	title: string
	/** Versioned logo path relative to the API root, or null when no logo is set. */
	logo_url: string | null
	logo_mime_type: string | null
	brand_color: string | null
	updated_at: string | null
}

/**
 * The branding resolved for the authenticated user: their customer's override
 * where one is configured, otherwise the global portal settings. `source` says
 * which one won, so the UI can be reasoned about without diffing values.
 */
export interface EffectivePortalBranding {
	title: string
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
	source: "custom" | "global"
	customer_code: string | null
}

export interface DashboardStats {
	total_alerts: number
	total_agents: number
	total_cases: number
}

export interface AlertsStats {
	total: number
	open: number
	in_progress: number
	closed: number
}

export interface CasesStats {
	total: number
	open: number
	in_progress: number
	closed: number
}
