import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '@/components/LoginPage.vue'

// Simple dashboard component template for now
const Dashboard = {
	template: `
		<div class="min-h-screen bg-gray-50">
			<header class="bg-white shadow">
				<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
					<div class="flex justify-between h-16">
						<div class="flex items-center">
							<h1 class="text-xl font-semibold">Customer Portal</h1>
						</div>
						<div class="flex items-center space-x-4">
							<span class="text-sm text-gray-700">{{ username }}</span>
							<button
								@click="logout"
								class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-md text-sm font-medium"
							>
								Logout
							</button>
						</div>
					</div>
				</div>
			</header>
			<main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
				<div class="px-4 py-6 sm:px-0">
					<div class="text-center">
						<h2 class="text-2xl font-bold text-gray-900 mb-4">Welcome to the Customer Portal</h2>
						<p class="text-gray-600">Your security dashboard is being prepared.</p>
						<p class="text-sm text-gray-500 mt-4">More features coming soon...</p>
					</div>
				</div>
			</main>
		</div>
	`,
	computed: {
		username() {
			try {
				const user = JSON.parse(localStorage.getItem('customer-portal-user') || '{}')
				return user.username || 'User'
			} catch {
				return 'User'
			}
		}
	},
	methods: {
		logout() {
			localStorage.removeItem('customer-portal-auth-token')
			localStorage.removeItem('customer-portal-user')
			this.$router.push('/login')
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
		name: 'Dashboard',
		component: Dashboard,
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