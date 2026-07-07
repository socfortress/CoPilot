import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const adminRoutes: RouteRecordRaw[] = [
	{
		path: "/customers",
		name: "Customers",
		component: () => import("@/views/Customers.vue"),
		meta: { title: "Customers", auth: true, roles: RouteRole.All }
	},
	{
		path: "/customers/:code",
		name: "Customer",
		component: () => import("@/views/Customer.vue"),
		meta: { title: "Customer", auth: true, roles: RouteRole.All }
	},
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
	},
	{
		path: "/logs",
		name: "Logs",
		component: () => import("@/views/Logs.vue"),
		meta: { title: "Logs", auth: true, roles: RouteRole.All }
	}
]
