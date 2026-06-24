import type { RouteRecordRaw } from "vue-router"
import { Layout } from "@/types/theme"

export const fallbackRoutes: RouteRecordRaw[] = [
	{
		path: "/:pathMatch(.*)*",
		name: "NotFound",
		component: () => import("@/views/NotFound.vue"),
		meta: {
			theme: { layout: Layout.Blank, boxed: { enabled: false }, padded: { enabled: false } },
			skipPin: true
		}
	}
]
