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
		path: "/audit",
		name: "Audit",
		component: () => import("@/views/Audit.vue"),
		meta: { title: "Audit", auth: true, roles: RouteRole.All }
	},
	{
		path: "/logs",
		name: "Logs",
		component: () => import("@/views/Logs.vue"),
		meta: { title: "Logs", auth: true, roles: RouteRole.All }
	},
	{
		path: "/users",
		name: "Users",
		component: () => import("@/views/Users.vue"),
		meta: { title: "Users", auth: true, roles: RouteRole.All }
	},
	{
		path: "/users/:id",
		name: "UserView",
		component: () => import("@/views/UserView.vue"),
		meta: { title: "User", auth: true, roles: RouteRole.All }
	}
]
