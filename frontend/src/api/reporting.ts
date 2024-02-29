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
		// TODO: remove
		/* for test
		const payload = {
			org_id: 44,
			dashboard_title: "string",
			dashboard_uid: "fd4ba63e-9e67-42cd-8fe7-f638cea19d7a",
			panel_ids: [5, 6, 7],
			time_range: {
				value: 1,
				unit: "hours"
			}
		}*/
		return HttpClient.post<FlaskBaseResponse & { links: PanelLink[] }>(`/reporting/generate_iframe_links`, payload)
	}
}
