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
	},
	{
		path: "/detection-catalog/wazuh-rules",
		redirect: "/detection-catalog"
	},
	{
		path: "/detection-catalog/wazuh-rules/:id",
		name: "DetectionCatalogWazuhRule",
		component: () => import("@/views/detectionCatalog/DetectionCatalogWazuhRule.vue"),
		meta: { title: "Wazuh Rule", auth: true, roles: RouteRole.All }
	},
	{
		path: "/detection-catalog/coverage-gaps",
		redirect: "/detection-catalog"
	},
	{
		path: "/detection-catalog/coverage-gaps/:techniqueId",
		name: "DetectionCatalogCoverageGap",
		component: () => import("@/views/detectionCatalog/DetectionCatalogCoverageGap.vue"),
		meta: { title: "Coverage Gap", auth: true, roles: RouteRole.All }
	},
	{
		path: "/detection-catalog/compliance",
		redirect: "/detection-catalog"
	},
	{
		path: "/detection-catalog/compliance/:framework",
		redirect: "/detection-catalog"
	},
	{
		path: "/detection-catalog/compliance/:framework/:control",
		name: "DetectionCatalogComplianceGroup",
		component: () => import("@/views/detectionCatalog/DetectionCatalogComplianceGroup.vue"),
		meta: { title: "Compliance Control", auth: true, roles: RouteRole.All }
	}
]
