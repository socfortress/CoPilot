import type { CommonResponse } from "@/types/common"
import type { AlertsStats, CasesStats, DashboardStats, PortalSettings } from "@/types/portal"
import { HttpClient } from "../httpClient"

export default {
	getSettings() {
		return HttpClient.get<CommonResponse<{ settings: PortalSettings }>>("/customer_portal/settings")
	},
	dashboardStats() {
		return HttpClient.get<CommonResponse<DashboardStats>>("/customer_portal/dashboard/stats")
	},
	alertsStats() {
		return HttpClient.get<CommonResponse<AlertsStats>>("/customer_portal/dashboard/alert-stats")
	},
	casesStats() {
		return HttpClient.get<CommonResponse<CasesStats>>("/customer_portal/dashboard/case-stats")
	}
}
