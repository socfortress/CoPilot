import type { Dashboard, Org, Panel, PanelLink } from "@/types/reporting"
import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"

export type PanelsLinksTimeUnit = "minutes" | "hours" | "days"

export interface PanelsLinksPayload {
	org_id: string | number
	dashboard_title: string
	dashboard_uid: string
	panel_ids: number[]
	time_range: {
		value: number
		unit: PanelsLinksTimeUnit
	}
}

export type RowPanelTimeUnit = "m" | "h" | "d"

export interface RowPanelPayload {
	org_id: number
	dashboard_title: string
	dashboard_uid: string
	panel_id: number
	panel_width: number
	panel_height: number
	theme: "light" | "dark"
}

export interface RowPayload {
	id: string | number
	panels: RowPanelPayload[]
}

export type ReportTimeRange = `${number}${RowPanelTimeUnit}`

export default {
	getOrgs() {
		return HttpClient.get<FlaskBaseResponse & { orgs: Org[] }>(`/reporting/orgs`)
	},
	getDashboards(orgId: string) {
		return HttpClient.get<FlaskBaseResponse & { dashboards: Dashboard[] }>(`/reporting/dashboards/${orgId}`)
	},
	getPanels(dashboardUID: string) {
		return HttpClient.get<FlaskBaseResponse & { panels: Panel[] }>(`/reporting/dashboard_panels/${dashboardUID}`)
	},
	generatePanelsLinks(payload: PanelsLinksPayload) {
		return HttpClient.post<FlaskBaseResponse & { links: PanelLink[] }>(`/reporting/generate_iframe_links`, payload)
	},
	generateReport(timerange: ReportTimeRange, rows: RowPayload[]) {
		return HttpClient.post<FlaskBaseResponse & { base64_result: string }>(
			`/reporting/generate-report`,
			// TODO: add real params
			{ timerange, timerange_text: "", logo_base64: "", company_name: "", rows },
			{ timeout: 0 }
		)
	}
}
