import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole } from "@/types/auth"

export const openCTIRoutes: RouteRecordRaw[] = [
	{
		path: "/opencti",
		name: "OpenCTI",
		component: () => import("@/views/OpenCTI.vue"),
		meta: { title: "OpenCTI", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst] }
	}
]
