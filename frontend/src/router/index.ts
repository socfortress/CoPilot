import { createRouter, createWebHistory } from "vue-router"
import Overview from "@/views/Overview.vue"
import Login from "@/views/auth/Login.vue"
import { UserRole } from "@/types/auth.d"
import { Layout } from "@/types/theme.d"
import { authCheck } from "@/utils/auth"
import type { FormType } from "@/components/auth/types.d"

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
			component: Overview,
			meta: { title: "Overview", auth: true, roles: UserRole.All }
		},
		{
			path: "/indices",
			name: "Indices",
			component: () => import("@/views/Indices.vue"),
			meta: { title: "Indices", auth: true, roles: UserRole.All }
		},
		{
			path: "/connectors",
			name: "Connectors",
			component: () => import("@/views/Connectors.vue"),
			meta: { title: "Connectors", auth: true, roles: UserRole.All }
		},
		{
			path: "/agents",
			meta: {
				auth: true,
				roles: UserRole.All
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
				}
			]
		},
		{
			path: "/graylog",
			redirect: "/graylog/management",
			meta: {
				auth: true,
				roles: UserRole.All
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
			name: "Alerts",
			component: () => import("@/views/Alerts.vue"),
			meta: { title: "Alerts", auth: true, roles: UserRole.All }
		},
		{
			path: "/artifacts",
			name: "Artifacts",
			component: () => import("@/views/Artifacts.vue"),
			meta: { title: "Artifacts", auth: true, roles: UserRole.All }
		},
		{
			path: "/soc",
			redirect: "/soc/alerts",
			meta: {
				auth: true,
				roles: UserRole.All
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
		{
			path: "/healthcheck",
			name: "Healthcheck",
			component: () => import("@/views/Healthcheck.vue"),
			meta: { title: "Healthcheck", auth: true, roles: UserRole.All }
		},
		{
			path: "/customers",
			name: "Customers",
			component: () => import("@/views/Customers.vue"),
			meta: { title: "Customers", auth: true, roles: UserRole.All }
		},
		{
			path: "/logs",
			name: "Logs",
			component: () => import("@/views/Logs.vue"),
			meta: { title: "Logs", auth: true, roles: UserRole.All }
		},
		{
			path: "/users",
			name: "Users",
			component: () => import("@/views/Users.vue"),
			meta: { title: "Users", auth: true, roles: UserRole.All }
		},
		{
			path: "/external-services",
			redirect: "/external-services/third-party-integrations",
			meta: {
				auth: true,
				roles: UserRole.All
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
				}
			]
		},
		{
			path: "/report-creation",
			name: "ReportCreation",
			component: () => import("@/views/ReportCreation.vue"),
			meta: { title: "Report Creation", auth: true, roles: UserRole.All }
		},
		{
			path: "/scheduler",
			name: "Scheduler",
			component: () => import("@/views/Scheduler.vue"),
			meta: { title: "Scheduler", auth: true, roles: UserRole.All }
		},
		{
			path: "/cloud-security-assessment",
			name: "CloudSecurityAssessment",
			component: () => import("@/views/CloudSecurityAssessment.vue"),
			meta: { title: "Cloud Sec. Assess.", auth: true, roles: UserRole.All }
		},
		{
			path: "/web-vulnerability-assessment",
			name: "WebVulnerabilityAssessment",
			component: () => import("@/views/WebVulnerabilityAssessment.vue"),
			meta: { title: "Web Vuln. Assess.", auth: true, roles: UserRole.All }
		},
		{
			path: "/license",
			meta: {
				auth: true,
				roles: UserRole.All
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
			meta: { title: "Profile", auth: true, roles: UserRole.All }
		},
		{
			path: "/login",
			name: "Login",
			component: Login,
			meta: { title: "Login", forceLayout: Layout.Blank, checkAuth: true, skipPin: true }
		},
		{
			path: "/register",
			name: "Register",
			component: Login,
			props: { formType: "signup" as FormType },
			meta: { title: "Register", forceLayout: Layout.Blank, checkAuth: true, skipPin: true }
		},
		{
			path: "/logout",
			name: "Logout",
			redirect: "/login"
		},
		{
			path: "/:pathMatch(.*)*",
			name: "NotFound",
			component: () => import("@/views/NotFound.vue"),
			meta: { forceLayout: Layout.Blank, skipPin: true }
		}
	]
})

router.beforeEach(route => {
	return authCheck(route)
})

export default router
