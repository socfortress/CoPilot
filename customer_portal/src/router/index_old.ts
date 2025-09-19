import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginPage from '@/components/LoginPage.vue'
// TODO: Add back when views are ready
// import AlertsView from '@/views/AlertsView.vue'
// import CasesView from '@/views/CasesView.vue'
const routes = [
	{
		path: '/login',
		name: 'Login',
		component: LoginPage,
		meta: { requiresGuest: true }
	},

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
							<span class="text-sm text-gray-700">{{ user?.username }}</span>
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
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div class="bg-white overflow-hidden shadow rounded-lg">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
											<span class="text-white font-medium">A</span>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="text-sm font-medium text-gray-500 truncate">
												Alerts
											</dt>
											<dd class="text-lg font-medium text-gray-900">
												View security alerts
											</dd>
										</dl>
									</div>
								</div>
							</div>
							<div class="bg-gray-50 px-5 py-3">
								<div class="text-sm">
									<router-link 
										to="/alerts" 
										class="font-medium text-blue-700 hover:text-blue-900"
									>
										View all alerts
									</router-link>
								</div>
							</div>
						</div>
						
						<div class="bg-white overflow-hidden shadow rounded-lg">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
											<span class="text-white font-medium">C</span>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="text-sm font-medium text-gray-500 truncate">
												Cases
											</dt>
											<dd class="text-lg font-medium text-gray-900">
												View security cases
											</dd>
										</dl>
									</div>
								</div>
							</div>
							<div class="bg-gray-50 px-5 py-3">
								<div class="text-sm">
									<router-link 
										to="/cases" 
										class="font-medium text-green-700 hover:text-green-900"
									>
										View all cases
									</router-link>
								</div>
							</div>
						</div>
					</div>
				</div>
			</main>
		</div>
	`,
	computed: {
		user() {
			const authStore = useAuthStore()
			return authStore.user
		}
	},
	methods: {
		logout() {
			const authStore = useAuthStore()
			authStore.logout()
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
				<a href="#/" class="mt-4 inline-block bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
					Go Home
				</a>
			</div>
		</div>
	`
}

const routes = [
	{
		path: '/login',
		name: 'Login',
		component: Login,
		meta: { requiresGuest: true }
	},
	{
		path: '/',
		name: 'Dashboard',
		component: Dashboard,
		meta: { requiresAuth: true }
	},
	// TODO: Add back when views are ready
	// {
	// 	path: '/alerts',
	// 	name: 'Alerts',
	// 	component: AlertsView,
	// 	meta: { requiresAuth: true }
	// },
	// {
	// 	path: '/cases',
	// 	name: 'Cases',
	// 	component: CasesView,
	// 	meta: { requiresAuth: true }
	// },
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

// Navigation guards
router.beforeEach((to, from, next) => {
	const authStore = useAuthStore()
	
	if (to.meta.requiresAuth && !authStore.isLogged) {
		next('/login')
	} else if (to.meta.requiresGuest && authStore.isLogged) {
		next('/')
	} else if (to.meta.requiresAuth && authStore.isLogged && !authStore.isCustomerUser) {
		// Ensure only customer users can access protected routes
		authStore.logout()
		next('/login')
	} else {
		next()
	}
})

export default router