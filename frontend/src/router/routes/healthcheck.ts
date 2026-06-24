import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const healthcheckRoutes: RouteRecordRaw[] = [
	{
		path: "/healthcheck",
		redirect: "/healthcheck/alerts",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "alerts",
				name: "Healthcheck",
				component: () => import("@/views/Healthcheck.vue"),
				meta: { title: "Healthcheck Alerts" }
			},
			{
				path: "metrics",
				name: "Metrics",
				component: () => import("@/views/Metrics.vue"),
				meta: { title: "Metrics Overview" }
			}
		]
	}
]
