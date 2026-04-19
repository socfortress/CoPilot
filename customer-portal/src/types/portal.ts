export interface PortalSettings {
	id: number
	title: string
	logo_base64: string
	logo_mime_type: string
	updated_at: string
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
