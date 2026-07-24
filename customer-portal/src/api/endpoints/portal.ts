import type { CommonResponse } from "@/types/common"
import type { AlertsStats, CasesStats, DashboardStats, EffectivePortalBranding, PortalSettings } from "@/types/portal"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

export default {
	/** Global defaults — public, used before login when no customer is known yet. */
	getSettings() {
		return HttpClient.get<CommonResponse<{ settings: PortalSettings }>>("/customer_portal/settings")
	},
	/** Branding for the authenticated user (per-customer override, else the global defaults). */
	getEffectiveSettings() {
		return HttpClient.get<CommonResponse<{ settings: EffectivePortalBranding }>>(
			"/customer_portal/settings/effective"
		)
	},
	dashboardStats(customerCodes?: string[]) {
		return HttpClient.get<CommonResponse<DashboardStats>>(
			"/customer_portal/dashboard/stats",
			withCustomerCodes(customerCodes)
		)
	},
	alertsStats(customerCodes?: string[]) {
		return HttpClient.get<CommonResponse<AlertsStats>>(
			"/customer_portal/dashboard/alert-stats",
			withCustomerCodes(customerCodes)
		)
	},
	casesStats(customerCodes?: string[]) {
		return HttpClient.get<CommonResponse<CasesStats>>(
			"/customer_portal/dashboard/case-stats",
			withCustomerCodes(customerCodes)
		)
	}
}
