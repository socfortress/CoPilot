import type { CommonResponse } from "@/types/common"
import type { PortalSettings } from "@/types/portal"
import { HttpClient } from "../httpClient"

export interface DashboardStats {
	total_alerts: number
	total_agents: number
	total_cases: number
}

export interface AlertsStats {
	total: number
	open: number
	in_progress: number
	closed: number
}

export default {
	getSettings() {
		return HttpClient.get<CommonResponse<{ settings: PortalSettings }>>("/customer_portal/settings")
	},
	dashboardStats() {
		return HttpClient.get<CommonResponse<DashboardStats>>("/customer_portal/dashboard/stats")
	},
	alertsStats() {
		return HttpClient.get<CommonResponse<AlertsStats>>("/customer_portal/dashboard/alert-stats")
	}
}
