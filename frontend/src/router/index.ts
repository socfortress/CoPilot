import { createRouter, createWebHistory } from "vue-router"
import Overview from "@/views/Overview.vue"
import Login from "@/views/Auth/Login.vue"
import { UserRole } from "@/types/auth.d"
import { Layout } from "@/types/theme.d"
import { authCheck } from "@/utils/auth"
import type { FormType } from "@/components/AuthForm/types.d"

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
					meta: { title: "Agent" }
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
			path: "/integrations",
			name: "Integrations",
			component: () => import("@/views/Integrations.vue"),
			meta: { title: "Integrations", auth: true, roles: UserRole.All }
		},
		{
			path: "/report-creation",
			name: "ReportCreation",
			component: () => import("@/views/ReportCreation.vue"),
			meta: { title: "Report Creation", auth: true, roles: UserRole.All }
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
					meta: { title: "License Success" }
				},
				{
					path: "cancel",
					name: "LicenseCancel",
					component: () => import("@/views/license/Cancel.vue"),
					meta: { title: "License Cancel" }
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
			meta: { title: "Login", forceLayout: Layout.Blank, checkAuth: true }
		},
		{
			path: "/register",
			name: "Register",
			component: () => import("@/views/Auth/Login.vue"),
			props: { formType: "signup" as FormType },
			meta: { title: "Register", forceLayout: Layout.Blank, checkAuth: true }
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
			meta: { forceLayout: Layout.Blank }
		}
	]
})

router.beforeEach(route => {
	return authCheck(route)
})

export default router
