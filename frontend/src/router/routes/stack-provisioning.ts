import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const stackProvisioningRoutes: RouteRecordRaw[] = [
	{
		path: "/stack-provisioning",
		name: "StackProvisioning",
		component: () => import("@/views/StackProvisioning.vue"),
		meta: { title: "Stack Provisioning", auth: true, roles: RouteRole.All }
	}
]
