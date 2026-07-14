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
				path: "exclusion-rules/new",
				name: "IncidentManagement-ExclusionRuleNew",
				component: () => import("@/views/incidentManagement/ExclusionRuleNew.vue"),
				meta: { title: "Create Exclusion Rule" }
			},
			{
				path: "exclusion-rules/:id",
				name: "IncidentManagement-ExclusionRule",
				component: () => import("@/views/incidentManagement/ExclusionRule.vue"),
				meta: { title: "Exclusion Rule" }
			},
			{
				path: "sources/new",
				name: "IncidentManagement-SourceNew",
				component: () => import("@/views/incidentManagement/ConfiguredSourceNew.vue"),
				meta: { title: "Create Source Configuration" }
			},
			{
				path: "sources",
				name: "IncidentManagement-Sources",
				component: () => import("@/views/incidentManagement/Sources.vue"),
				meta: { title: "Incident Sources" }
			},
			{
				path: "sources/:source",
				name: "IncidentManagement-Source",
				component: () => import("@/views/incidentManagement/ConfiguredSource.vue"),
				meta: { title: "Incident Source" }
			},
			{
				path: "alerts",
				name: "IncidentManagement-Alerts",
				component: () => import("@/views/incidentManagement/Alerts.vue"),
				meta: { title: "Incident Alerts" }
			},
			{
				path: "alerts/:alertId/assets",
				redirect: to => ({
					name: "IncidentManagement-Alert",
					params: { id: to.params.alertId }
				})
			},
			{
				path: "alerts/:alertId/assets/:assetId",
				name: "IncidentManagement-AlertAsset",
				component: () => import("@/views/incidentManagement/AlertLinkedAsset.vue"),
				meta: { title: "Alert Asset" }
			},
			{
				path: "alerts/:alertId/iocs",
				redirect: to => ({
					name: "IncidentManagement-Alert",
					params: { id: to.params.alertId }
				})
			},
			{
				path: "alerts/:alertId/iocs/new",
				name: "IncidentManagement-AlertIocNew",
				component: () => import("@/views/incidentManagement/AlertLinkedIocNew.vue"),
				meta: { title: "Create Alert IoC" }
			},
			{
				path: "alerts/:alertId/iocs/:iocId",
				name: "IncidentManagement-AlertIoc",
				component: () => import("@/views/incidentManagement/AlertLinkedIoc.vue"),
				meta: { title: "Alert IoC" }
			},
			{
				path: "alerts/:id",
				name: "IncidentManagement-Alert",
				component: () => import("@/views/incidentManagement/Alert.vue"),
				meta: { title: "Incident Alert" }
			},
			{
				path: "cases/new",
				name: "IncidentManagement-CaseNew",
				component: () => import("@/views/incidentManagement/CaseNew.vue"),
				meta: { title: "Create Case" }
			},
			{
				path: "cases/:id",
				name: "IncidentManagement-Case",
				component: () => import("@/views/incidentManagement/Case.vue"),
				meta: { title: "Incident Case" }
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
