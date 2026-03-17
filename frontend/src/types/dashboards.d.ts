export interface DashboardPanel {
	id: string
	title: string
	type: string
	w: number
	h: number
	lucene: string
	field?: string
	size?: number
}

export interface DashboardTemplate {
	id: string
	title: string
	description: string
	panels: DashboardPanel[]
}

export interface DashboardCategory {
	id: string
	title: string
	description: string
	vendor: string
	product: string
	event_type: string
	tags: string[]
	color: string
	icon: string
}

export interface DashboardCategoryWithTemplates extends DashboardCategory {
	templates: DashboardTemplate[]
}

export interface EnabledDashboard {
	id: number
	customer_code: string
	event_source_id: number
	library_card: string
	template_id: string
	display_name: string
	created_at: string
}

export interface EnableDashboardPayload {
	customer_code: string
	event_source_id: number
	library_card: string
	template_id: string
	display_name: string
}

export interface PanelResult {
	type: string
	value: number | null
	labels: string[]
	data: number[]
	error: string | null
}

export interface PanelDataResponse {
	panels: Record<string, PanelResult>
	template: DashboardTemplate
	dashboard_id: number
	accent_color: string
	success: boolean
	message: string
}
