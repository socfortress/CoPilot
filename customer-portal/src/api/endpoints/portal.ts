import type { PortalProfile } from "@/types/auth"
import type { CommonResponse } from "@/types/common"
import type {
	AlertsStats,
	CasesStats,
	DashboardStats,
	EffectivePortalBranding,
	OverviewTrend,
	OverviewTrendRange,
	PortalOverview,
	PortalSettings
} from "@/types/portal"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

export default {
	/** Global defaults — public, used before login when no customer is known yet. */
	getSettings() {
		return HttpClient.get<CommonResponse<{ settings: PortalSettings }>>("/customer_portal/settings", {
			keepOnNavigation: true
		})
	},
	/** Branding for the authenticated user (per-customer override, else the global defaults). */
	getEffectiveSettings() {
		return HttpClient.get<CommonResponse<{ settings: EffectivePortalBranding }>>(
			"/customer_portal/settings/effective",
			{ keepOnNavigation: true }
		)
	},
	/** The portal user and their customers, with names. Not page-scoped: the whole session reads it. */
	me() {
		return HttpClient.get<CommonResponse<PortalProfile>>("/customer_portal/me", { keepOnNavigation: true })
	},
	/** Everything the Overview renders, in one call. */
	overview(options: { recentLimit: number; aiLimit: number; customerCodes?: string[]; signal?: AbortSignal }) {
		return HttpClient.get<CommonResponse<PortalOverview>>(
			"/customer_portal/overview",
			withCustomerCodes(options.customerCodes, {
				params: { recent_limit: options.recentLimit, ai_limit: options.aiLimit },
				signal: options.signal
			})
		)
	},
	/** The Overview's trend: a call of its own, so the Overview itself stays one light request. */
	overviewTrend(options: { range: OverviewTrendRange; customerCodes?: string[]; signal?: AbortSignal }) {
		return HttpClient.get<CommonResponse<OverviewTrend>>(
			"/customer_portal/overview/trend",
			withCustomerCodes(options.customerCodes, { params: { range: options.range }, signal: options.signal })
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
