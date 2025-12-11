import { createRouter, createWebHistory } from "vue-router"
import LoginPage from "@/components/LoginPage.vue"
import OverviewPage from "@/views/OverviewPage.vue"
import AlertsPage from "@/views/AlertsPage.vue"
import CasesPage from "@/views/CasesPage.vue"
import CaseDetailsView from "@/views/CaseDetailsView.vue"
import AgentsPage from "@/views/AgentsPage.vue"
import AccessDenied from '@/components/common/AccessDenied.vue'

const NotFound = {
	template: `
		<div class="min-h-screen flex items-center justify-center bg-gray-50">
			<div class="text-center">
				<h1 class="text-4xl font-bold text-gray-900">404</h1>
				<p class="mt-2 text-lg text-gray-600">Page not found</p>
				<router-link to="/" class="mt-4 inline-block bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
					Go Home
				</router-link>
			</div>
		</div>
	`
}

const routes = [
	{
		path: "/login",
		name: "Login",
		component: LoginPage,
		meta: { requiresGuest: true }
	},
	{
		path: "/",
		name: "Overview",
		component: OverviewPage,
		meta: { requiresAuth: true }
	},
	{
		path: "/overview",
		redirect: "/"
	},
	{
		path: "/alerts",
		name: "Alerts",
		component: AlertsPage,
		meta: { requiresAuth: true }
	},
	{
		path: "/cases",
		name: "Cases",
		component: CasesPage,
		meta: { requiresAuth: true }
	},
	{
		path: "/cases/:id",
		name: "CaseDetails",
		component: CaseDetailsView,
		meta: { requiresAuth: true }
	},
	{
		path: "/agents",
		name: "Agents",
		component: AgentsPage,
		meta: { requiresAuth: true }
	},
    {
        path: '/access-denied',
        name: 'AccessDenied',
        component: AccessDenied,
        meta: { requiresAuth: false }
    },
	{
		path: "/:pathMatch(.*)*",
		name: "NotFound",
		component: NotFound
	}
]

const router = createRouter({
	history: createWebHistory(),
	routes
})

// Simple navigation guards
router.beforeEach((to, _from, next) => {
	const token = localStorage.getItem("customer-portal-auth-token")
	const isAuthenticated = !!token

	if (to.meta.requiresAuth && !isAuthenticated) {
		next("/login")
	} else if (to.meta.requiresGuest && isAuthenticated) {
		next("/")
	} else {
		next()
	}
})

export default router
