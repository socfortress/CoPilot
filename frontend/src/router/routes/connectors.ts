import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const connectorsRoutes: RouteRecordRaw[] = [
	{
		path: "/connectors",
		name: "Connectors",
		component: () => import("@/views/Connectors.vue"),
		meta: { title: "Connectors", auth: true, roles: RouteRole.All }
	}
]
