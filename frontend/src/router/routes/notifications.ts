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
		// Declared above the `:id` route: vue-router ranks a static segment over a
		// param anyway, but keeping the order explicit means the next path added
		// here doesn't have to rely on that.
		path: "/internal-notifications/new",
		name: "InternalNotificationNew",
		component: () => import("@/views/notification/InternalNotificationRouteNew.vue"),
		meta: { title: "Create Internal Notification Route", auth: true, roles: AuthUserRole.Admin }
	},
	{
		path: "/internal-notifications/:id",
		name: "InternalNotification",
		component: () => import("@/views/notification/InternalNotificationRoute.vue"),
		meta: { title: "Internal Notification Route", auth: true, roles: AuthUserRole.Admin, skipPin: true }
	},
	{
		// Templates are shared across tenants — one edit changes what every
		// route using it sends — so they live outside the per-customer tree and
		// are admin-only, same reasoning as internal routes above.
		path: "/message-templates",
		name: "MessageTemplates",
		component: () => import("@/views/notification/MessageTemplates.vue"),
		meta: { title: "Message Templates", auth: true, roles: AuthUserRole.Admin }
	},
	{
		path: "/message-templates/new",
		name: "MessageTemplateNew",
		component: () => import("@/views/notification/MessageTemplateNew.vue"),
		meta: { title: "Create Message Template", auth: true, roles: AuthUserRole.Admin }
	},
	{
		path: "/message-templates/:id",
		name: "MessageTemplate",
		component: () => import("@/views/notification/MessageTemplate.vue"),
		meta: { title: "Message Template", auth: true, roles: AuthUserRole.Admin, skipPin: true }
	}
]
