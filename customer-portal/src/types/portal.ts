export interface PortalSettings {
	id: number
	title: string
	logo_base64: string
	logo_mime_type: string
	updated_at: string
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
