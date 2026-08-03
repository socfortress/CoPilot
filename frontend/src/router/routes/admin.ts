import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole, RouteRole } from "@/types/auth"

export const adminRoutes: RouteRecordRaw[] = [
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
		// Internal notification routes are deployment-wide configuration —
		// where the SOC's own assignment notifications go — so they sit outside
		// the per-customer tree and are admin-only, unlike a customer's routes
		// which an analyst can manage.
		path: "/internal-notifications",
		name: "InternalNotifications",
		component: () => import("@/views/InternalNotificationRoutes.vue"),
		meta: { title: "Internal Notifications", auth: true, roles: AuthUserRole.Admin }
	},
	{
		// Templates are shared across tenants — one edit changes what every
		// route using it sends — so they live outside the per-customer tree and
		// are admin-only, same reasoning as internal routes above.
		path: "/notification-templates",
		name: "NotificationTemplates",
		component: () => import("@/views/NotificationTemplates.vue"),
		meta: { title: "Message Templates", auth: true, roles: AuthUserRole.Admin }
	},
	{
		path: "/logs",
		name: "Logs",
		component: () => import("@/views/Logs.vue"),
		meta: { title: "Logs", auth: true, roles: RouteRole.All }
	}
]
