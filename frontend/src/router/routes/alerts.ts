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
				path: "mitre/techniques/:techniqueId",
				name: "Alerts-Mitre-Techniques",
				component: () => import("@/views/alerts/MitreTechniques.vue"),
				meta: { title: "MITRE Technique" }
			},
			{
				path: "mitre/techniques",
				redirect: { name: "Alerts-Mitre" }
			},
			{
				path: "mitre/tactics/:tacticId",
				name: "Alerts-Mitre-Tactic",
				component: () => import("@/views/alerts/MitreTactic.vue"),
				meta: { title: "MITRE Tactic" }
			},
			{
				path: "mitre/tactics",
				redirect: { name: "Alerts-Mitre" }
			},
			{
				path: "mitre/software/:softwareId",
				name: "Alerts-Mitre-Software",
				component: () => import("@/views/alerts/MitreSoftware.vue"),
				meta: { title: "MITRE Software" }
			},
			{
				path: "mitre/software",
				redirect: { name: "Alerts-Mitre" }
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
				path: "mitre/:techniqueId/events/:eventId",
				name: "Alerts-Mitre-Technique-Event",
				component: () => import("@/views/alerts/MitreTechniqueEvent.vue"),
				meta: { title: "MITRE Technique Alert" }
			},
			{
				path: "mitre/:techniqueId/events",
				redirect: to => ({
					name: "Alerts-Mitre-Technique",
					params: { techniqueId: to.params.techniqueId }
				})
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
