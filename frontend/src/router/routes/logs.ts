import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const logsRoutes: RouteRecordRaw[] = [
	{
		path: "/logs",
		name: "Logs",
		component: () => import("@/views/Logs.vue"),
		meta: { title: "Logs", auth: true, roles: RouteRole.All }
	}
]
