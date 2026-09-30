import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole } from "@/types/auth"

// SOCFortress UBA (user behavior analytics): entities ranked by risk, UBA alerts, suppressions.
// The connector (URL + API key) is configured under Connectors; this page is for using it.
export const ubaRoutes: RouteRecordRaw[] = [
	{
		path: "/uba",
		name: "Uba",
		component: () => import("@/views/Uba.vue"),
		meta: { title: "User Behavior Analytics", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst] }
	}
]
