import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const licenseRoutes: RouteRecordRaw[] = [
	{
		path: "/license",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "",
				name: "License",
				component: () => import("@/views/license/License.vue"),
				meta: { title: "License" }
			},
			{
				path: "success",
				name: "LicenseSuccess",
				component: () => import("@/views/license/Success.vue"),
				meta: { title: "License Success", skipPin: true }
			},
			{
				path: "cancel",
				name: "LicenseCancel",
				component: () => import("@/views/license/Cancel.vue"),
				meta: { title: "License Cancel", skipPin: true }
			}
		]
	}
]
