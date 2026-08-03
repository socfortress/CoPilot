import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const auditRoutes: RouteRecordRaw[] = [
	{
		path: "/audit",
		name: "Audit",
		component: () => import("@/views/Audit.vue"),
		meta: { title: "Audit", auth: true, roles: RouteRole.All }
	},
	{
		path: "/audit/:id",
		name: "AuditEntry",
		component: () => import("@/views/AuditEntry.vue"),
		meta: { title: "Audit Entry", auth: true, roles: RouteRole.All }
	}
]
