import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole, RouteRole } from "@/types/auth"

export const incidentManagementRoutes: RouteRecordRaw[] = [
	/*
	{
		path: "/soc",
		redirect: "/soc/alerts",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "alerts",
				name: "Soc-Alerts",
				component: () => import("@/views/soc/Alerts.vue"),
				meta: { title: "SOC Alerts" }
			},
			{
				path: "cases",
				name: "Soc-Cases",
				component: () => import("@/views/soc/Cases.vue"),
				meta: { title: "SOC Cases" }
			},
			{
				path: "users",
				name: "Soc-Users",
				component: () => import("@/views/soc/Users.vue"),
				meta: { title: "SOC Users" }
			},
			{
				path: "pending-alerts",
				name: "Soc-PendingAlerts",
				component: () => import("@/views/soc/PendingAlerts.vue"),
				meta: { title: "SOC Pending Alerts" }
			}
		]
	},
	*/
	{
		path: "/incident-management",
		redirect: "/incident-management/alerts",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "sources/:source",
				name: "IncidentManagement-Source",
				component: () => import("@/views/incidentManagement/ConfiguredSource.vue"),
				meta: { title: "Incident Source" }
			},
			{
				path: "sources",
				name: "IncidentManagement-Sources",
				component: () => import("@/views/incidentManagement/Sources.vue"),
				meta: { title: "Incident Sources" }
			},
			{
				path: "alerts",
				name: "IncidentManagement-Alerts",
				component: () => import("@/views/incidentManagement/Alerts.vue"),
				meta: { title: "Incident Alerts" }
			},
			{
				path: "alerts/:id",
				name: "IncidentManagement-Alert",
				component: () => import("@/views/incidentManagement/Alert.vue"),
				meta: { title: "Incident Alert" }
			},
			{
				path: "cases",
				name: "IncidentManagement-Cases",
				component: () => import("@/views/incidentManagement/Cases.vue"),
				meta: { title: "Incident Cases" }
			},
			{
				path: "case-templates",
				name: "IncidentManagement-CaseTemplates",
				component: () => import("@/views/incidentManagement/CaseTemplates.vue"),
				meta: {
					title: "Case Templates",
					// Admin/analyst only — templates are SOC-team-managed playbooks.
					roles: [AuthUserRole.Admin, AuthUserRole.Analyst]
				}
			},
			{
				path: "sigma",
				name: "IncidentManagement-Sigma",
				component: () => import("@/views/incidentManagement/Sigma.vue"),
				meta: { title: "Sigma rules" }
			}
		]
	}
]
