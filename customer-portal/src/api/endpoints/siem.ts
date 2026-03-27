import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"

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
}

export default {
	getCustomerCodes() {
		return HttpClient.get<CommonResponse<{ customer_codes: string[] }>>("/auth/me/customers")
	},

	getEventSources(customerCode: string) {
		return HttpClient.get<CommonResponse<{ event_sources: EventSource[] }>>(`/siem/event_sources/${customerCode}`)
	},

	queryEvents(
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
	) {
		return HttpClient.get<
			CommonResponse<{ events: EventSearchResult[]; total: number; scroll_id: string | null; page_size: number }>
		>(`/siem/events/${customerCode}/${sourceName}`, { params })
	},

	getFieldMappings(customerCode: string, sourceName: string) {
		return HttpClient.get<CommonResponse<{ fields: FieldMapping[]; total: number; index_pattern: string }>>(
			`/siem/events/${customerCode}/${sourceName}/fields`
		)
	},

	getEnabledDashboards(customerCode: string) {
		return HttpClient.get<CommonResponse<{ enabled_dashboards: EnabledDashboard[] }>>(
			`/siem/dashboards/enabled/${customerCode}`
		)
	},

	getPanelData(dashboardId: number, timerange: string, signal?: AbortSignal) {
		return HttpClient.post<CommonResponse<PanelDataResponse>>(
			`/siem/dashboards/panel-data`,
			{ dashboard_id: dashboardId, timerange },
			signal ? { signal } : {}
		)
	}
}
