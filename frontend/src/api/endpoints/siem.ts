import type {
	CustomDashboard,
	CustomDashboardCreatePayload,
	CustomDashboardDefinition,
	CustomDashboardImportPayload,
	CustomDashboardPreviewPayload,
	CustomDashboardPreviewResponse,
	CustomDashboardUpdatePayload,
	DashboardCategory,
	DashboardCategoryWithTemplates,
	EnableDashboardPayload,
	EnabledDashboard,
	PanelDataResponse
} from "@/types/dashboards"
import type { DisplayColumn, EventSource } from "@/types/event-sources"
import type { EventSearchResult, FieldMapping } from "@/types/events"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export interface EventSourceCreatePayload {
	customer_code: string
	name: string
	index_pattern: string
	event_type: string
	time_field: string
	enabled: boolean
	displayed_columns?: DisplayColumn[] | null
}

export interface EventSourceUpdatePayload {
	name?: string
	index_pattern?: string
	event_type?: string
	time_field?: string
	enabled?: boolean
	displayed_columns?: DisplayColumn[] | null
}

export interface SiemEventDocumentQuery {
	index_name: string
	event_id: string
}

export default {
	getEventSources(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { event_sources: EventSource[] }>(
			`/siem/event_sources/${customerCode}`,
			{ signal }
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
		query: {
			customerCode: string
			sourceName: string
			params: {
				timerange?: string
				page_size?: number
				scroll_id?: string
				query?: string
				time_from?: string
				time_to?: string
			}
		},
		signal?: AbortSignal
	) {
		return HttpClient.get<
			FlaskBaseResponse & {
				events: EventSearchResult[]
				total: number
				scroll_id: string | null
				page_size: number
			}
		>(`/siem/events/${query.customerCode}/${query.sourceName}`, { params: query.params, signal })
	},
	getEvent(customerCode: string, sourceName: string, query: SiemEventDocumentQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { event: EventSearchResult }>(
			`/siem/events/${customerCode}/${sourceName}/document`,
			signal ? { params: query, signal } : { params: query }
		)
	},
	getFieldMappings(customerCode: string, sourceName: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { fields: FieldMapping[]; total: number; index_pattern: string }>(
			`/siem/events/${customerCode}/${sourceName}/fields`,
			{ signal }
		)
	},

	// ── Dashboards ──────────────────────────────────────────────
	getDashboardCategories(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { categories: DashboardCategory[] }>(`/siem/dashboards/templates`, {
			signal
		})
	},
	getDashboardCategory(categoryId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { category: DashboardCategoryWithTemplates }>(
			`/siem/dashboards/templates/${categoryId}`,
			{ signal }
		)
	},
	getEnabledDashboards(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { enabled_dashboards: EnabledDashboard[] }>(
			`/siem/dashboards/enabled/${customerCode}`,
			{ signal }
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
	getPanelData(dashboardId: number, timerange: string, signal?: AbortSignal) {
		return HttpClient.post<FlaskBaseResponse & PanelDataResponse>(
			`/siem/dashboards/panel-data`,
			{
				dashboard_id: dashboardId,
				timerange
			},
			signal ? { signal } : {}
		)
	},

	// ── Custom dashboards ───────────────────────────────────────
	getCustomDashboards(query: { customerCode?: string | null }, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { custom_dashboards: CustomDashboard[] }>(`/siem/dashboards/custom`, {
			params: query.customerCode ? { customer_code: query.customerCode } : {},
			signal
		})
	},
	getCustomDashboard(templateKey: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { custom_dashboard: CustomDashboard }>(
			`/siem/dashboards/custom/${templateKey}`,
			{ signal }
		)
	},
	createCustomDashboard(payload: CustomDashboardCreatePayload) {
		return HttpClient.post<FlaskBaseResponse & { custom_dashboard: CustomDashboard }>(
			`/siem/dashboards/custom`,
			payload
		)
	},
	updateCustomDashboard(templateKey: string, payload: CustomDashboardUpdatePayload) {
		return HttpClient.put<FlaskBaseResponse & { custom_dashboard: CustomDashboard }>(
			`/siem/dashboards/custom/${templateKey}`,
			payload
		)
	},
	deleteCustomDashboard(templateKey: string) {
		return HttpClient.delete<FlaskBaseResponse & { disabled_dashboards: number }>(
			`/siem/dashboards/custom/${templateKey}`
		)
	},
	importCustomDashboard(payload: CustomDashboardImportPayload) {
		return HttpClient.post<FlaskBaseResponse & { custom_dashboard: CustomDashboard }>(
			`/siem/dashboards/custom/import`,
			payload
		)
	},
	exportCustomDashboard(templateKey: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { definition: CustomDashboardDefinition }>(
			`/siem/dashboards/custom/${templateKey}/export`,
			{ signal }
		)
	},
	previewCustomDashboard(payload: CustomDashboardPreviewPayload, signal?: AbortSignal) {
		return HttpClient.post<FlaskBaseResponse & CustomDashboardPreviewResponse>(
			`/siem/dashboards/custom/preview`,
			payload,
			signal ? { signal } : {}
		)
	}
}
