import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole } from "@/types/auth"

export const threatIntelRoutes: RouteRecordRaw[] = [
	{
		path: "/threat-intel",
		name: "ThreatIntel",
		component: () => import("@/views/ThreatIntel.vue"),
		meta: { title: "Threat Intel", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst] }
	},
	{
		// OpenCTI had its own page before #1153; keep old links and bookmarks working.
		// That page kept its sub-view in `?tab=` (lookup | indicators), which is
		// `?view=` on the OpenCTI tab now that `?tab=` picks the source.
		path: "/opencti",
		name: "OpenCTI",
		redirect: to => {
			const { tab, ...query } = to.query
			const view = tab === "lookup" || tab === "indicators" ? { view: tab } : {}
			return { name: "ThreatIntel", query: { ...query, ...view, tab: "opencti" } }
		}
	}
]
