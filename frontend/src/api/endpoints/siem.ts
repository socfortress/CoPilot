import type {
	DashboardCategory,
	DashboardCategoryWithTemplates,
	EnableDashboardPayload,
	EnabledDashboard,
	PanelDataResponse
} from "@/types/dashboards.d"
import type { EventSearchResult, FieldMapping } from "@/types/events.d"
import type { EventSource } from "@/types/eventSources.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface EventSourceCreatePayload {
	customer_code: string
	name: string
	index_pattern: string
	event_type: string
	time_field: string
	enabled: boolean
}

export interface EventSourceUpdatePayload {
	name?: string
	index_pattern?: string
	event_type?: string
	time_field?: string
	enabled?: boolean
}

export default {
	getEventSources(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { event_sources: EventSource[] }>(
			`/siem/event_sources/${customerCode}`
		)
	},
	createEventSource(payload: EventSourceCreatePayload) {
		return HttpClient.post<FlaskBaseResponse & { event_source: EventSource }>(`/siem/event_sources`, payload)
	},
	updateEventSource(eventSourceId: number, payload: EventSourceUpdatePayload) {
		return HttpClient.put<FlaskBaseResponse & { event_source: EventSource }>(
			`/siem/event_sources/${eventSourceId}`,
			payload
		)
	},
	deleteEventSource(eventSourceId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/siem/event_sources/${eventSourceId}`)
	},
	queryEvents(
		customerCode: string,
		sourceName: string,
		params: { timerange?: string; page_size?: number; scroll_id?: string; query?: string }
	) {
		return HttpClient.get<
			FlaskBaseResponse & {
				events: EventSearchResult[]
				total: number
				scroll_id: string | null
				page_size: number
			}
		>(`/siem/events/${customerCode}/${sourceName}`, { params })
	},
	getFieldMappings(customerCode: string, sourceName: string) {
		return HttpClient.get<FlaskBaseResponse & { fields: FieldMapping[]; total: number; index_pattern: string }>(
			`/siem/events/${customerCode}/${sourceName}/fields`
		)
	},

	// ── Dashboards ──────────────────────────────────────────────
	getDashboardCategories() {
		return HttpClient.get<FlaskBaseResponse & { categories: DashboardCategory[] }>(`/siem/dashboards/templates`)
	},
	getDashboardCategory(categoryId: string) {
		return HttpClient.get<FlaskBaseResponse & { category: DashboardCategoryWithTemplates }>(
			`/siem/dashboards/templates/${categoryId}`
		)
	},
	getEnabledDashboards(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { enabled_dashboards: EnabledDashboard[] }>(
			`/siem/dashboards/enabled/${customerCode}`
		)
	},
	enableDashboard(payload: EnableDashboardPayload) {
		return HttpClient.post<FlaskBaseResponse & { enabled_dashboard: EnabledDashboard }>(
			`/siem/dashboards/enable`,
			payload
		)
	},
	disableDashboard(dashboardId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/siem/dashboards/disable/${dashboardId}`)
	},
	getPanelData(dashboardId: number, timerange: string) {
		return HttpClient.post<PanelDataResponse>(`/siem/dashboards/panel-data`, {
			dashboard_id: dashboardId,
			timerange
		})
	}
}
