<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="bg-white shadow">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<router-link to="/" class="mr-4 text-indigo-600 hover:text-indigo-500">
							← Back to Dashboard
						</router-link>
						<h1 class="text-xl font-semibold">Security Alerts</h1>
					</div>
					<div class="flex items-center space-x-4">
						<span class="text-sm text-gray-700">{{ user?.username }}</span>
						<button
							@click="logout"
							class="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<main class="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
			<div class="px-4 py-6 sm:px-0">
				<!-- Loading State -->
				<div v-if="loading" class="py-8 text-center">
					<div
						class="inline-flex items-center rounded-md bg-indigo-500 px-4 py-2 text-sm leading-6 font-semibold text-white shadow"
					>
						Loading alerts...
					</div>
				</div>

				<!-- Error State -->
				<div v-else-if="error" class="rounded-md border border-red-200 bg-red-50 p-4">
					<div class="flex">
						<div class="ml-3">
							<h3 class="text-sm font-medium text-red-800">Error loading alerts</h3>
							<div class="mt-2 text-sm text-red-700">
								{{ error }}
							</div>
						</div>
					</div>
				</div>

				<!-- Alerts List -->
				<div v-else>
					<!-- Stats Cards -->
					<div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-red-500">
										<span class="text-sm font-medium text-white">H</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">High</p>
										<p class="text-lg font-semibold text-gray-900">{{ getAlertCount("high") }}</p>
									</div>
								</div>
							</div>
						</div>
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-yellow-500">
										<span class="text-sm font-medium text-white">M</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">Medium</p>
										<p class="text-lg font-semibold text-gray-900">{{ getAlertCount("medium") }}</p>
									</div>
								</div>
							</div>
						</div>
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-blue-500">
										<span class="text-sm font-medium text-white">L</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">Low</p>
										<p class="text-lg font-semibold text-gray-900">{{ getAlertCount("low") }}</p>
									</div>
								</div>
							</div>
						</div>
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-gray-500">
										<span class="text-sm font-medium text-white">T</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">Total</p>
										<p class="text-lg font-semibold text-gray-900">{{ alerts.length }}</p>
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Alerts Table -->
					<div class="overflow-hidden bg-white shadow sm:rounded-md">
						<div class="px-4 py-5 sm:px-6">
							<h3 class="text-lg leading-6 font-medium text-gray-900">Recent Alerts</h3>
							<p class="mt-1 max-w-2xl text-sm text-gray-500">Security alerts for your organization</p>
						</div>

						<div v-if="alerts.length === 0" class="px-4 py-5 text-center text-gray-500 sm:px-6">
							No alerts found
						</div>

						<ul v-else class="divide-y divide-gray-200">
							<li v-for="alert in alerts" :key="alert.id" class="px-4 py-4 sm:px-6">
								<div class="flex items-center justify-between">
									<div class="flex items-center">
										<div
											class="mr-3 h-3 w-3 rounded-full"
											:class="{
												'bg-red-500': alert.alert_severity === 'high',
												'bg-yellow-500': alert.alert_severity === 'medium',
												'bg-blue-500': alert.alert_severity === 'low',
												'bg-gray-500': !alert.alert_severity
											}"
										></div>
										<div>
											<p class="text-sm font-medium text-gray-900">
												{{ alert.alert_name || "Unnamed Alert" }}
											</p>
											<p class="text-sm text-gray-500">
												{{ alert.alert_description || "No description available" }}
											</p>
											<p class="mt-1 text-xs text-gray-400">
												Created: {{ formatDate(alert.alert_creation_time) }}
											</p>
										</div>
									</div>
									<div class="flex items-center space-x-2">
										<span
											class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
											:class="{
												'bg-red-100 text-red-800': alert.alert_severity === 'high',
												'bg-yellow-100 text-yellow-800': alert.alert_severity === 'medium',
												'bg-blue-100 text-blue-800': alert.alert_severity === 'low',
												'bg-gray-100 text-gray-800': !alert.alert_severity
											}"
										>
											{{ alert.alert_severity || "Unknown" }}
										</span>
										<span
											class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
											:class="{
												'bg-green-100 text-green-800': alert.alert_status === 'resolved',
												'bg-red-100 text-red-800': alert.alert_status === 'open',
												'bg-yellow-100 text-yellow-800': alert.alert_status === 'in_progress',
												'bg-gray-100 text-gray-800': !alert.alert_status
											}"
										>
											{{ alert.alert_status || "Unknown" }}
										</span>
									</div>
								</div>
							</li>
						</ul>
					</div>

					<!-- Pagination (if needed) -->
					<div v-if="alerts.length > 0" class="mt-6 flex justify-center">
						<button
							@click="refreshAlerts"
							class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
						>
							Refresh
						</button>
					</div>
				</div>
			</div>
		</main>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { httpClient } from "@/utils/httpClient"

interface Alert {
	id: number
	alert_name: string
	alert_description: string
	alert_severity: string
	alert_status: string
	alert_creation_time: string
	customer_code?: string
}

const router = useRouter()
const authStore = useAuthStore()

const alerts = ref<Alert[]>([])
const loading = ref(false)
const error = ref("")

const user = computed(() => authStore.user)

const getAlertCount = (severity: string) => {
	return alerts.value.filter(alert => alert.alert_severity === severity).length
}

const formatDate = (dateString: string) => {
	if (!dateString) return "Unknown"
	try {
		return new Date(dateString).toLocaleDateString()
	} catch {
		return "Invalid date"
	}
}

const fetchAlerts = async () => {
	loading.value = true
	error.value = ""

	try {
		const response = await httpClient.get("/alerts/")
		alerts.value = response.data || []
	} catch (err: any) {
		error.value = err.response?.data?.detail || "Failed to fetch alerts"
		console.error("Failed to fetch alerts:", err)
	} finally {
		loading.value = false
	}
}

const refreshAlerts = () => {
	fetchAlerts()
}

const logout = () => {
	authStore.logout()
	router.push("/login")
}

onMounted(() => {
	fetchAlerts()
})
</script>
