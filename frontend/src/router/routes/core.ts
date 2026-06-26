import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"
import OverviewPage from "@/views/Overview.vue"

export const coreRoutes: RouteRecordRaw[] = [
	{
		path: "/",
		redirect: "/overview"
	},
	{
		path: "/overview",
		name: "Overview",
		component: OverviewPage,
		meta: { title: "Overview", auth: true, roles: RouteRole.All }
	}
]
