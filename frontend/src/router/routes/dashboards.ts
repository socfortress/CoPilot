import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole, RouteRole } from "@/types/auth"

export const dashboardsRoutes: RouteRecordRaw[] = [
	{
		path: "/dashboards",
		name: "Dashboards",
		component: () => import("@/views/dashboards/Dashboards.vue"),
		meta: { title: "Dashboards", auth: true, roles: RouteRole.All }
	},
	{
		path: "/dashboards/:id",
		name: "DashboardView",
		component: () => import("@/views/dashboards/DashboardView.vue"),
		meta: { title: "Dashboard Viewer", auth: true, roles: RouteRole.All, skipPin: true }
	},
	{
		path: "/artifacts",
		name: "Artifacts",
		component: () => import("@/views/Artifacts.vue"),
		meta: { title: "Artifacts", auth: true, roles: RouteRole.All }
	},
	{
		path: "/file-analysis",
		name: "FileAnalysis",
		component: () => import("@/views/NewFileAnalysis.vue"),
		meta: { title: "File Analysis", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst] }
	},
	{
		// Split from the landing page rather than an optional :jobId? param, so the
		// two states are separate route records: each loads only its own chunk, and
		// neither carries the other's mounted logic.
		path: "/file-analysis/:jobId",
		name: "FileAnalysisDetails",
		component: () => import("@/views/FileAnalysisDetails.vue"),
		// Its own title, and skipPin like every other detail route: sharing the
		// parent's title pinned "File Analysis" twice in the toolbar.
		meta: {
			title: "File Analysis Result",
			auth: true,
			roles: [AuthUserRole.Admin, AuthUserRole.Analyst],
			skipPin: true
		}
	}
]
