import type { CommonResponse } from "@/types/common"
import type { PortalSettings } from "@/types/portal"
import { HttpClient } from "../httpClient"

export interface DashboardStats {
	total_alerts: number
	total_agents: number
	total_cases: number
}

export default {
	getSettings() {
		return HttpClient.get<CommonResponse<{ settings: PortalSettings }>>("/customer_portal/settings")
	},
	dashBoardStats() {
		return HttpClient.get<CommonResponse<DashboardStats>>("/customer_portal/dashboard/stats")
	}
}
