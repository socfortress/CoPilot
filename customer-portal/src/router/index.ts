import type { FormType } from "@/components/auth/types"
import { createRouter, createWebHistory } from "vue-router"
import { AuthUserRole, RouteRole } from "@/types/auth"
import { Layout } from "@/types/theme"
import { authCheck } from "@/utils/auth"
import AuthPage from "@/views/Auth.vue"
import Overview from "@/views/Overview.vue"

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
			meta: { title: "Overview", auth: true, roles: RouteRole.All }
		},
		{
			path: "/alerts",
			meta: {
				auth: true,
				roles: RouteRole.All
			},
			children: [
				{
					path: "",
					name: "AlertsList",
					component: () => import("@/views/Alerts/Overview.vue"),
					meta: { title: "Alerts" }
				},
				{
					path: ":id",
					name: "AlertOverview",
					component: () => import("@/views/Alerts/AlertsView.vue"),
					meta: { title: "Alert Details", skipPin: true }
				}
			]
		},
		{
			path: "/cases",
			meta: {
				auth: true,
				roles: RouteRole.All
			},
			children: [
				{
					path: "",
					name: "CasesList",
					component: () => import("@/views/Cases/List.vue"),
					meta: { title: "Cases" }
				},
				{
					path: ":id",
					name: "CaseOverview",
					component: () => import("@/views/Cases/Overview.vue"),
					meta: { title: "Case Details", skipPin: true }
				}
			]
		},
		{
			path: "/agents",
			name: "Agents",
			component: () => import("@/views/Agents.vue"),
			meta: { title: "Agents", auth: true, roles: RouteRole.All }
		},
		{
			path: "/event-search",
			name: "EventSearch",
			component: () => import("@/views/EventSearch.vue"),
			meta: { title: "Event Search", auth: true, roles: RouteRole.All }
		},
		{
			path: "/dashboards",
			meta: {
				auth: true,
				roles: RouteRole.All
			},
			children: [
				{
					path: "",
					name: "DashboardsList",
					component: () => import("@/views/Dashboards/List.vue"),
					meta: { title: "Dashboards" }
				},
				{
					path: ":id",
					name: "DashboardOverview",
					component: () => import("@/views/Dashboards/Overview.vue"),
					meta: { title: "Dashboard Details", skipPin: true }
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
