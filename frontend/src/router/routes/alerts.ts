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
				path: "siem/alert/:indexName/:alertId",
				name: "Alerts-SIEM-Alert",
				component: () => import("@/views/alerts/AlertsSiemAlert.vue"),
				meta: { title: "SIEM Alert" }
			},
			{
				path: "siem/alert/:indexName",
				redirect: to => ({
					name: "Alerts-SIEM-Summary",
					params: { indexName: to.params.indexName }
				})
			},
			{
				path: "siem/alert",
				redirect: { name: "Alerts-SIEM" }
			},
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
				path: "mitre/mitigations/:mitigationId",
				name: "Alerts-Mitre-Mitigation",
				component: () => import("@/views/alerts/MitreMitigation.vue"),
				meta: { title: "MITRE Mitigation" }
			},
			{
				path: "mitre/mitigations",
				redirect: { name: "Alerts-Mitre" }
			},
			{
				path: "mitre/groups/:groupId",
				name: "Alerts-Mitre-Group",
				component: () => import("@/views/alerts/MitreGroup.vue"),
				meta: { title: "MITRE Group" }
			},
			{
				path: "mitre/groups",
				redirect: { name: "Alerts-Mitre" }
			},
			{
				path: "mitre/:techniqueId",
				name: "Alerts-Mitre-Technique",
				component: () => import("@/views/alerts/MitreTechniqueAlert.vue"),
				meta: { title: "MITRE Technique" }
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
