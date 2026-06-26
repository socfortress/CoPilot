import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const analystRoutes: RouteRecordRaw[] = [
	{
		path: "/ai-analyst",
		name: "AiAnalyst",
		component: () => import("@/views/AiAnalyst.vue"),
		meta: { title: "AI Analyst", auth: true, roles: RouteRole.All }
	},
	{
		path: "/detection-catalog",
		name: "DetectionCatalog",
		component: () => import("@/views/DetectionCatalog.vue"),
		meta: { title: "Detections Catalog", auth: true, roles: RouteRole.All }
	}
]
