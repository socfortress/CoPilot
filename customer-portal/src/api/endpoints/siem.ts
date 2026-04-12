import type { CommonResponse } from "@/types/common"
import type {
	EnabledDashboard,
	EventSearchResult,
	EventSourceItem,
	FieldMapping,
	PanelDataResponse
} from "@/types/siem"
import { HttpClient } from "../httpClient"

export default {
	getEventSources(customerCode: string) {
		return HttpClient.get<CommonResponse<{ event_sources: EventSourceItem[] }>>(
			`/siem/event_sources/${customerCode}`
		)
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
