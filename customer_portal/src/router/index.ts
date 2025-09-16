import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '@/components/LoginPage.vue'
import OverviewPage from '@/views/OverviewPage.vue'

// Helper function to create placeholder components
const createPlaceholderComponent = (title: string, description: string) => {
	return {
		template: `
			<div class="min-h-screen bg-gray-50">
				<header class="bg-white shadow-sm border-b">
					<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
						<div class="flex justify-between h-16">
							<div class="flex items-center">
								<button @click="goBack" class="mr-4 text-indigo-600 hover:text-indigo-500">
									← Back
								</button>
								<h1 class="text-xl font-semibold text-gray-900">${title}</h1>
							</div>
						</div>
					</div>
				</header>
				<main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
					<div class="px-4 py-6 sm:px-0">
						<div class="text-center py-12">
							<h2 class="text-2xl font-bold text-gray-900 mb-4">${title}</h2>
							<p class="text-gray-600 mb-8">${description}</p>
							<div class="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
								<p class="text-blue-800 text-sm">
									This feature is coming soon. We're working on bringing you comprehensive ${title.toLowerCase()} management.
								</p>
							</div>
						</div>
					</div>
				</main>
			</div>
		`,
		methods: {
			goBack() {
				this.$router.push('/')
			}
		}
	}
}

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
		path: '/login',
		name: 'Login',
		component: LoginPage,
		meta: { requiresGuest: true }
	},
	{
		path: '/',
		name: 'Overview',
		component: OverviewPage,
		meta: { requiresAuth: true }
	},
	{
		path: '/overview',
		redirect: '/'
	},
	{
		path: '/alerts',
		name: 'Alerts',
		component: () => createPlaceholderComponent('Alerts', 'Security alerts for your organization'),
		meta: { requiresAuth: true }
	},
	{
		path: '/cases',
		name: 'Cases',
		component: () => createPlaceholderComponent('Cases', 'Security incident cases'),
		meta: { requiresAuth: true }
	},
	{
		path: '/:pathMatch(.*)*',
		name: 'NotFound',
		component: NotFound
	}
]

const router = createRouter({
	history: createWebHistory(),
	routes
})

// Simple navigation guards
router.beforeEach((to, _from, next) => {
	const token = localStorage.getItem('customer-portal-auth-token')
	const isAuthenticated = !!token

	if (to.meta.requiresAuth && !isAuthenticated) {
		next('/login')
	} else if (to.meta.requiresGuest && isAuthenticated) {
		next('/')
	} else {
		next()
	}
})

export default router
