import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const settingsRoutes: RouteRecordRaw[] = [
	{
		path: "/sso-config",
		name: "SSOConfig",
		component: () => import("@/views/SSOConfig.vue"),
		meta: { title: "SSO Config", auth: true, roles: RouteRole.All }
	},
	{
		path: "/profile",
		name: "Profile",
		component: () => import("@/views/Profile.vue"),
		meta: { title: "Profile", auth: true, roles: RouteRole.All }
	}
]
