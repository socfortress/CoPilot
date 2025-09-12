import type { FormType } from "@/components/auth/types.d"
import { createRouter, createWebHistory } from "vue-router"
import { RouteRole } from "@/types/auth.d"
import { Layout } from "@/types/theme.d"
import { authCheck } from "@/utils/auth"
import AuthPage from "@/views/Auth.vue"
import OverviewPage from "@/views/Overview.vue"

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes: [
		{
			path: "/",
			redirect: "/overview"
		},
		{
			path: "/overview",
			name: "Overview",
			component: OverviewPage,
			meta: { title: "Overview", auth: true, roles: RouteRole.All }
		},
		{
			path: "/indices",
			name: "Indices",
			component: () => import("@/views/Indices.vue"),
			meta: { title: "Indices", auth: true, roles: RouteRole.All }
		},
		{
			path: "/connectors",
			name: "Connectors",
			component: () => import("@/views/Connectors.vue"),
			meta: { title: "Connectors", auth: true, roles: RouteRole.All }
		},
		{
			path: "/agents",
			meta: {
				auth: true,
				roles: RouteRole.All
			},
			children: [
				{
					path: "",
					name: "Agents",
					component: () => import("@/views/agents/Agents.vue"),
					meta: { title: "Agents" }
				},
				{
					path: ":id",
					name: "Agent",
					component: () => import("@/views/agents/Overview.vue"),
					meta: { title: "Agent", skipPin: true }
				},
				{
					path: "sysmon-config",
					name: "SysmonConfig",
					component: () => import("@/views/agents/SysmonConfig.vue"),
					meta: { title: "Sysmon Config" }
				},
				{
					path: "detection-rules",
					name: "DetectionRules",
					component: () => import("@/views/agents/DetectionRules.vue"),
					meta: { title: "Detection Rules" }
				},
				{
					path: "groups",
					name: "Groups",
					component: () => import("@/views/agents/Groups.vue"),
					meta: { title: "Groups" }
				},
				{
					path: "copilot-actions",
					name: "CopilotActions",
					component: () => import("@/views/agents/CopilotActions.vue"),
					meta: { title: "CoPilot Actions" }
				},
				{
					path: "vulnerability-overview",
					name: "VulnerabilityOverview",
					component: () => import("@/views/agents/VulnerabilityOverview.vue"),
					meta: { title: "Vulnerability Overview" }
				},
				{
					path: "sca-overview",
					name: "ScaOverview",
					component: () => import("@/views/agents/ScaOverview.vue"),
					meta: { title: "SCA Overview" }
				}
			]
		},
		{
			path: "/graylog",
			redirect: "/graylog/management",
			meta: {
				auth: true,
				roles: RouteRole.All
			},
			children: [
				{
					path: "management",
					name: "Graylog-Management",
					component: () => import("@/views/graylog/Management.vue"),
					meta: { title: "Graylog Management" }
				},
				{
					path: "metrics",
					name: "Graylog-Metrics",
					component: () => import("@/views/graylog/Metrics.vue"),
					meta: { title: "Graylog Metrics" }
				},
				{
					path: "pipelines",
					name: "Graylog-Pipelines",
					component: () => import("@/views/graylog/Pipelines.vue"),
					meta: { title: "Graylog Pipelines" }
				}
			]
		},
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
		},
		{
			path: "/artifacts",
			name: "Artifacts",
			component: () => import("@/views/Artifacts.vue"),
			meta: { title: "Artifacts", auth: true, roles: RouteRole.All }
		},
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
					path: "cases",
					name: "IncidentManagement-Cases",
					component: () => import("@/views/incidentManagement/Cases.vue"),
					meta: { title: "Incident Cases" }
				},
				{
					path: "sigma",
					name: "IncidentManagement-Sigma",
					component: () => import("@/views/incidentManagement/Sigma.vue"),
					meta: { title: "Sigma rules" }
				}
			]
		},
		{
			path: "/healthcheck",
			name: "Healthcheck",
			component: () => import("@/views/Healthcheck.vue"),
			meta: { title: "Healthcheck", auth: true, roles: RouteRole.All }
		},
		{
			path: "/customers",
			name: "Customers",
			component: () => import("@/views/Customers.vue"),
			meta: { title: "Customers", auth: true, roles: RouteRole.All }
		},
		{
			path: "/logs",
			name: "Logs",
			component: () => import("@/views/Logs.vue"),
			meta: { title: "Logs", auth: true, roles: RouteRole.All }
		},
		{
			path: "/users",
			name: "Users",
			component: () => import("@/views/Users.vue"),
			meta: { title: "Users", auth: true, roles: RouteRole.All }
		},
		{
			path: "/external-services",
			redirect: "/external-services/third-party-integrations",
			meta: {
				auth: true,
				roles: RouteRole.All
			},
			children: [
				{
					path: "third-party-integrations",
					name: "ExternalServices-ThirdPartyIntegrations",
					component: () => import("@/views/externalServices/ThirdPartyIntegrations.vue"),
					meta: { title: "Third Party Integrations" }
				},
				{
					path: "network-connectors",
					name: "ExternalServices-NetworkConnectors",
					component: () => import("@/views/externalServices/NetworkConnectors.vue"),
					meta: { title: "Network Connectors" }
				},
				{
					path: "singul-app-auth",
					name: "ExternalServices-SingulAppAuth",
					component: () => import("@/views/externalServices/SingulAppAuth.vue"),
					meta: { title: "Singul App Auth" }
				}
			]
		},
		{
			path: "/report-creation",
			name: "ReportCreation",
			component: () => import("@/views/ReportCreation.vue"),
			meta: { title: "Report Creation", auth: true, roles: RouteRole.All }
		},
		{
			path: "/scheduler",
			name: "Scheduler",
			component: () => import("@/views/Scheduler.vue"),
			meta: { title: "Scheduler", auth: true, roles: RouteRole.All }
		},
		{
			path: "/cloud-security-assessment",
			name: "CloudSecurityAssessment",
			component: () => import("@/views/CloudSecurityAssessment.vue"),
			meta: { title: "Cloud Sec. Assess.", auth: true, roles: RouteRole.All }
		},
		{
			path: "/web-vulnerability-assessment",
			name: "WebVulnerabilityAssessment",
			component: () => import("@/views/WebVulnerabilityAssessment.vue"),
			meta: { title: "Web Vuln. Assess.", auth: true, roles: RouteRole.All }
		},
		{
			path: "/license",
			meta: {
				auth: true,
				roles: RouteRole.All
			},
			children: [
				{
					path: "",
					name: "License",
					component: () => import("@/views/license/License.vue"),
					meta: { title: "License" }
				},
				{
					path: "success",
					name: "LicenseSuccess",
					component: () => import("@/views/license/Success.vue"),
					meta: { title: "License Success", skipPin: true }
				},
				{
					path: "cancel",
					name: "LicenseCancel",
					component: () => import("@/views/license/Cancel.vue"),
					meta: { title: "License Cancel", skipPin: true }
				}
			]
		},

		{
			path: "/profile",
			name: "Profile",
			component: () => import("@/views/Profile.vue"),
			meta: { title: "Profile", auth: true, roles: RouteRole.All }
		},
		{
			path: "/login",
			name: "Login",
			component: AuthPage,
			props: { formType: "signin" as FormType },
			meta: {
				title: "Login",
				theme: { layout: Layout.Blank, boxed: { enabled: false }, padded: { enabled: false } },
				checkAuth: true,
				skipPin: true
			}
		},
		/*
		{
			path: "/register",
			name: "Register",
			component: AuthPage,
			props: { formType: "signup" as FormType },
			meta: {
				title: "Register",
				theme: { layout: Layout.Blank, boxed: { enabled: false }, padded: { enabled: false } },
				checkAuth: true,
				skipPin: true
			}
		},
		*/
		{
			path: "/logout",
			name: "Logout",
			redirect: "/login"
		},
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
})

router.beforeEach(route => {
	return authCheck(route)
})

export default router
