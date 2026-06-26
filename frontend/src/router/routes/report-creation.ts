import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const reportCreationRoutes: RouteRecordRaw[] = [
	// {
	// 	path: "/report-creation",
	// 	name: "ReportCreation",
	// 	component: () => import("@/views/ReportCreation.vue"),
	// 	meta: { title: "Report Creation", auth: true, roles: RouteRole.All }
	// },
	{
		path: "/report-creation",
		redirect: "/report-creation/general",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "general",
				name: "ReportCreation",
				component: () => import("@/views/ReportCreation.vue"),
				meta: { title: "General Reports" }
			},
			{
				path: "vulnerability-reports",
				name: "VulnerabilityReports",
				component: () => import("@/components/vulnerabilities/VulnerabilityReports.vue"),
				meta: { title: "Vulnerability Reports" }
			},
			{
				path: "sca-reports",
				name: "SCAReports",
				component: () => import("@/components/sca/SCAReports.vue"),
				meta: { title: "SCA Reports" }
			}
		]
	}
]
