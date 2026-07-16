import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

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
		meta: { title: "Dashboard Viewer", auth: true, roles: RouteRole.All }
	},
	{
		path: "/artifacts",
		name: "Artifacts",
		component: () => import("@/views/Artifacts.vue"),
		meta: { title: "Artifacts", auth: true, roles: RouteRole.All }
	}
]
