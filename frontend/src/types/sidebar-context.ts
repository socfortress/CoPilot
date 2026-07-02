export type SidebarIndicatorStatus = "ok" | "warning" | "error"

export interface SidebarHealthIndicator {
	id: string
	status: SidebarIndicatorStatus
	label: string
	detail?: string | null
	count?: number | null
	category?: string | null
}

export interface SidebarContextResponse {
	success: boolean
	message: string
	current_version: string
	latest_version: string | null
	is_outdated: boolean
	release_url?: string | null
	environment: string
	indicators: SidebarHealthIndicator[]
}
