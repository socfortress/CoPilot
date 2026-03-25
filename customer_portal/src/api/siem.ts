import { httpClient } from "@/utils/httpClient"

export interface EventSource {
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
	success: boolean
	message: string
}

export class SiemAPI {
	static async getCustomerCodes(): Promise<{ success: boolean; customer_codes: string[] }> {
		return (await httpClient.get("/auth/me/customers")).data
	}

	static async getEventSources(
		customerCode: string
	): Promise<{ success: boolean; message: string; event_sources: EventSource[] }> {
		return (await httpClient.get(`/siem/event_sources/${customerCode}`)).data
	}

	static async queryEvents(
		customerCode: string,
		sourceName: string,
		params: {
			timerange?: string
			page_size?: number
			scroll_id?: string
			query?: string
			time_from?: string
			time_to?: string
		}
	): Promise<{
		success: boolean
		message: string
		events: EventSearchResult[]
		total: number
		scroll_id: string | null
		page_size: number
	}> {
		return (await httpClient.get(`/siem/events/${customerCode}/${sourceName}`, { params })).data
	}

	static async getFieldMappings(
		customerCode: string,
		sourceName: string
	): Promise<{
		success: boolean
		message: string
		fields: FieldMapping[]
		total: number
		index_pattern: string
	}> {
		return (await httpClient.get(`/siem/events/${customerCode}/${sourceName}/fields`)).data
	}

	static async getEnabledDashboards(
		customerCode: string
	): Promise<{ success: boolean; enabled_dashboards: EnabledDashboard[] }> {
		return (await httpClient.get(`/siem/dashboards/enabled/${customerCode}`)).data
	}

	static async getPanelData(
		dashboardId: number,
		timerange: string,
		signal?: AbortSignal
	): Promise<PanelDataResponse> {
		return (
			await httpClient.post(
				`/siem/dashboards/panel-data`,
				{ dashboard_id: dashboardId, timerange },
				signal ? { signal } : {}
			)
		).data
	}
}
