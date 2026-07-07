import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const detectionCatalogRoutes: RouteRecordRaw[] = [
	{
		path: "/detection-catalog",
		name: "DetectionCatalog",
		component: () => import("@/views/detectionCatalog/DetectionCatalog.vue"),
		meta: { title: "Detections Catalog", auth: true, roles: RouteRole.All }
	},
	{
		path: "/detection-catalog/stories",
		redirect: "/detection-catalog"
	},
	{
		path: "/detection-catalog/stories/:name",
		name: "DetectionCatalogStory",
		component: () => import("@/views/detectionCatalog/DetectionCatalogStory.vue"),
		meta: { title: "Analytic Story", auth: true, roles: RouteRole.All }
	},
	{
		path: "/detection-catalog/detections",
		redirect: "/detection-catalog"
	},
	{
		path: "/detection-catalog/detections/:id",
		name: "DetectionCatalogDetection",
		component: () => import("@/views/detectionCatalog/DetectionCatalogDetection.vue"),
		meta: { title: "Detection Rule", auth: true, roles: RouteRole.All }
	}
]
