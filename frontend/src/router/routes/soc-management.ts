import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole } from "@/types/auth"

// SOC Management & SLA (#1187): service performance for SOC managers. Analysts see every
// aggregate and only their own per-analyst row; only admins edit SLA policies.
export const socManagementRoutes: RouteRecordRaw[] = [
	{
		path: "/soc-management",
		name: "SocManagement",
		component: () => import("@/views/SocManagement.vue"),
		meta: { title: "SOC Management", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst] }
	}
]
