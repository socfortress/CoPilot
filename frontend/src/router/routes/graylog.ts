import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const graylogRoutes: RouteRecordRaw[] = [
	{
		path: "/graylog",
		redirect: "/graylog/management",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "management",
				name: "Graylog-Management",
				component: () => import("@/views/graylog/Management.vue"),
				meta: { title: "Graylog Management" }
			},
			{
				path: "metrics",
				name: "Graylog-Metrics",
				component: () => import("@/views/graylog/Metrics.vue"),
				meta: { title: "Graylog Metrics" }
			},
			{
				path: "pipelines",
				name: "Graylog-Pipelines",
				component: () => import("@/views/graylog/Pipelines.vue"),
				meta: { title: "Graylog Pipelines" }
			}
		]
	}
]
