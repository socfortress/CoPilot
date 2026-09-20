import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const activeResponseRoutes: RouteRecordRaw[] = [
	{
		path: "/active-response",
		name: "ActiveResponse",
		component: () => import("@/views/ActiveResponse.vue"),
		meta: { title: "Active Response", auth: true, roles: RouteRole.All }
	}
]
