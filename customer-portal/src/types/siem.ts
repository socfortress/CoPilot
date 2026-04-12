export interface EventSourceItem {
	id: number
	customer_code: string
	name: string
	index_pattern: string
	event_type: string
	time_field: string
	enabled: boolean
	created_at: string
	updated_at: string
}

export interface EventSearchResult {
	[key: string]: any
}

export interface FieldMapping {
	field: string
	type: string
}

export type DashboardPanelType = "stat" | "pie" | "bar_h" | "histogram"

export interface DashboardPanel {
	id: string
	title: string
	type: DashboardPanelType
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

export interface EnabledDashboard {
	id: number
	customer_code: string
	event_source_id: number
	library_card: string
	template_id: string
	display_name: string
	created_at: string
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
	customer_code: string
	source_name: string
	accent_color: string
}
