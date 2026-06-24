import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const indicesRoutes: RouteRecordRaw[] = [
	{
		path: "/indices",
		redirect: "/indices/management",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "management",
				name: "Indices",
				component: () => import("@/views/Indices.vue"),
				meta: { title: "Index Management" }
			},
			{
				path: "snapshots",
				name: "Snapshots",
				component: () => import("@/views/Snapshots.vue"),
				meta: { title: "Snapshot & Restore" }
			}
		]
	}
]
