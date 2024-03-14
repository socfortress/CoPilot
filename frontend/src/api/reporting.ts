import type { Dashboard, Org, Panel, PanelLink, PanelImage } from "@/types/reporting"
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
	generateReport(rows: Array<{ id: number }>[]) {
		return HttpClient.post<FlaskBaseResponse & { base64_images: PanelImage[] }>(
			`/reporting/generate-report`,
			{
				timerange: "1h",
				rows
			},
			{ timeout: 0 }
		)
	}
}
