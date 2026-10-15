import type { CommonResponse } from "@/types/common"
import type {
	DisplayColumn,
	EnabledDashboard,
	EventSearchMemory,
	EventSearchResult,
	EventSearchState,
	EventSourceItem,
	FieldMapping,
	PanelDataResponse
} from "@/types/siem"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

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

	// -- Event search memory (#1258): the caller's saved and recent searches and columns.
	// Every call answers with the whole memory. The read is cached by the page, so it is
	// not page-scoped: a cancelled read would leave the cache waiting forever.
	getEventSearchMemory(customerCode: string) {
		return HttpClient.get<CommonResponse<EventSearchMemory>>(`/siem/event_search/${customerCode}`, {
			keepOnNavigation: true
		})
	},

	saveEventSearchQuery(customerCode: string, name: string, state: EventSearchState) {
		return HttpClient.post<CommonResponse<EventSearchMemory & { replaced: boolean }>>(
			`/siem/event_search/${customerCode}/saved`,
			{ ...state, name }
		)
	},

	deleteEventSearchQuery(customerCode: string, queryId: number) {
		return HttpClient.delete<CommonResponse<EventSearchMemory>>(`/siem/event_search/${customerCode}/saved/${queryId}`)
	},

	rememberEventSearch(customerCode: string, state: EventSearchState) {
		return HttpClient.post<CommonResponse<EventSearchMemory>>(`/siem/event_search/${customerCode}/recent`, state)
	},

	clearEventSearchRecent(customerCode: string) {
		return HttpClient.delete<CommonResponse<EventSearchMemory>>(`/siem/event_search/${customerCode}/recent`)
	},

	setEventSearchColumns(customerCode: string, sourceName: string, columns: DisplayColumn[] | null) {
		return HttpClient.put<CommonResponse<EventSearchMemory>>(`/siem/event_search/${customerCode}/columns`, {
			source_name: sourceName,
			columns
		})
	},

	getEnabledDashboards(customerCode: string) {
		return HttpClient.get<CommonResponse<{ enabled_dashboards: EnabledDashboard[] }>>(
			`/siem/dashboards/enabled/${customerCode}`
		)
	},

	getEnabledDashboardsForCustomers(customerCodes?: string[], signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<{ enabled_dashboards: EnabledDashboard[] }>>(
			"/siem/dashboards/enabled",
			withCustomerCodes(customerCodes, { signal })
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
