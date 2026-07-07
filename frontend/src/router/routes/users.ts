import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const usersRoutes: RouteRecordRaw[] = [
	{
		path: "/users",
		name: "Users",
		component: () => import("@/views/users/Users.vue"),
		meta: { title: "Users", auth: true, roles: RouteRole.All }
	},
	{
		path: "/users/:id",
		name: "UserView",
		component: () => import("@/views/users/UserView.vue"),
		meta: { title: "User", auth: true, roles: RouteRole.All }
	}
]
