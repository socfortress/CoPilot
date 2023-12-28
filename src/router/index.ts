import { createRouter, createWebHistory } from "vue-router"
import Indices from "@/views/socfortress/Indices.vue"
import { UserRole } from "@/types/auth.d"
import { Layout } from "@/types/theme.d"
import { authCheck } from "@/utils/auth"

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes: [
		{
			path: "/",
			redirect: "/indices"
		},
		{
			path: "/indices",
			name: "Indices",
			component: Indices,
			meta: { title: "Indices", auth: true, roles: UserRole.All }
		},
		{
			path: "/connectors",
			name: "Connectors",
			component: () => import("@/views/socfortress/Connectors.vue"),
			meta: { title: "Connectors", auth: true, roles: UserRole.All }
		},
		{
			path: "/agents",
			name: "Agents",
			component: () => import("@/views/socfortress/Agents.vue"),
			meta: { title: "Agents", auth: true, roles: UserRole.All }
		},
		{
			path: "/agent/:id?",
			name: "Agent",
			component: () => import("@/views/socfortress/AgentOverview.vue"),
			meta: { title: "Agent", auth: true, roles: UserRole.All }
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
					component: () => import("@/views/socfortress/graylog/Management.vue"),
					meta: { title: "Graylog Management" }
				},
				{
					path: "metrics",
					name: "Graylog-Metrics",
					component: () => import("@/views/socfortress/graylog/Metrics.vue"),
					meta: { title: "Graylog Metrics" }
				},
				{
					path: "pipelines",
					name: "Graylog-Pipelines",
					component: () => import("@/views/socfortress/graylog/Pipelines.vue"),
					meta: { title: "Graylog Pipelines" }
				}
			]
		},
		{
			path: "/alerts",
			name: "Alerts",
			component: () => import("@/views/socfortress/Alerts.vue"),
			meta: { title: "Alerts", auth: true, roles: UserRole.All }
		},
		{
			path: "/artifacts",
			name: "Artifacts",
			component: () => import("@/views/socfortress/Artifacts.vue"),
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
					component: () => import("@/views/socfortress/soc/Alerts.vue"),
					meta: { title: "SOC Alerts" }
				},
				{
					path: "cases",
					name: "Soc-Cases",
					component: () => import("@/views/socfortress/soc/Cases.vue"),
					meta: { title: "SOC Cases" }
				},
				{
					path: "users",
					name: "Soc-Users",
					component: () => import("@/views/socfortress/soc/Users.vue"),
					meta: { title: "SOC Users" }
				}
			]
		},
		{
			path: "/healthcheck",
			name: "Healthcheck",
			component: () => import("@/views/socfortress/Healthcheck.vue"),
			meta: { title: "Healthcheck", auth: true, roles: UserRole.All }
		},
		{
			path: "/customers",
			name: "Customers",
			component: () => import("@/views/socfortress/Customers.vue"),
			meta: { title: "Customers", auth: true, roles: UserRole.All }
		},
		{
			path: "/logs",
			name: "Logs",
			component: () => import("@/views/socfortress/Logs.vue"),
			meta: { title: "Logs", auth: true, roles: UserRole.All }
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
			component: () => import("@/views/Auth/Login.vue"),
			meta: { title: "Login", forceLayout: Layout.Blank, checkAuth: true }
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
