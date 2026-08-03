import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole } from "@/types/auth"

export const notificationsRoutes: RouteRecordRaw[] = [
	{
		// Internal notification routes are deployment-wide configuration —
		// where the SOC's own assignment notifications go — so they sit outside
		// the per-customer tree and are admin-only, unlike a customer's routes
		// which an analyst can manage.
		path: "/internal-notifications",
		name: "InternalNotifications",
		component: () => import("@/views/notification/InternalNotificationRoutes.vue"),
		meta: { title: "Internal Notifications", auth: true, roles: AuthUserRole.Admin }
	},
	{
		// Templates are shared across tenants — one edit changes what every
		// route using it sends — so they live outside the per-customer tree and
		// are admin-only, same reasoning as internal routes above.
		path: "/message-templates",
		name: "MessageTemplates",
		component: () => import("@/views/notification/MessageTemplates.vue"),
		meta: { title: "Message Templates", auth: true, roles: AuthUserRole.Admin }
	}
]
