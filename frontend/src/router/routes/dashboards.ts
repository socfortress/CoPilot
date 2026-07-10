import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const dashboardsRoutes: RouteRecordRaw[] = [
	{
		path: "/event-search/:customerCode/:sourceName/:indexName/:eventId",
		name: "EventSearch-Event",
		component: () => import("@/views/events/Event.vue"),
		meta: { title: "Event", auth: true, roles: RouteRole.All }
	},
	{
		path: "/event-search",
		name: "EventSearch",
		component: () => import("@/views/EventSearch.vue"),
		meta: { title: "Event Search", auth: true, roles: RouteRole.All }
	},
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
