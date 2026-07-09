import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const alertsRoutes: RouteRecordRaw[] = [
	{
		path: "/alerts",
		redirect: "/alerts/siem",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "siem",
				name: "Alerts-SIEM",
				component: () => import("@/views/alerts/AlertsGraylog.vue"),
				meta: { title: "SIEM" }
			},
			{
				path: "siem/:indexName",
				name: "Alerts-SIEM-Summary",
				component: () => import("@/views/alerts/AlertsSiemSummary.vue"),
				meta: { title: "SIEM Alert Summary" }
			},
			{
				path: "mitre",
				name: "Alerts-Mitre",
				component: () => import("@/views/alerts/Mitre.vue"),
				meta: { title: "MITRE ATT&CK" }
			},
			{
				path: "atomic-red-team",
				name: "Alerts-AtomicRedTeam",
				component: () => import("@/views/alerts/AtomicRedTeam.vue"),
				meta: { title: "Atomic Red Team" }
			}
		]
	}
]
