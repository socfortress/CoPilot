<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="border-b bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<div class="mr-3 min-h-8">
							<img
								v-if="portalLogo && showLogo"
								class="h-8 w-auto"
								:src="portalLogo"
								:alt="portalTitle"
								@error="showLogo = false"
							/>
						</div>
						<h1 class="text-xl font-semibold text-gray-900">{{ portalTitle }}</h1>
						<nav class="ml-8 flex space-x-8">
							<router-link
								to="/"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Overview
							</router-link>
							<router-link
								to="/alerts"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Cases
							</router-link>
							<router-link
								to="/agents"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Agents
							</router-link>
							<router-link
								to="/event-search"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Event Search
							</router-link>
							<router-link
								to="/dashboards"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
							>
								Dashboards
							</router-link>
						</nav>
					</div>
					<div class="flex items-center space-x-4">
						<div class="text-sm text-gray-700">
							Welcome,
							<span class="font-medium">{{ username }}</span>
						</div>
						<button
							@click="logout"
							class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<!-- Customer Selector -->
			<div class="mb-6 rounded-lg bg-white shadow">
				<div class="px-4 py-5 sm:p-6">
					<div class="grid grid-cols-1 gap-4 md:grid-cols-4">
						<div>
							<label for="customer-select" class="block text-sm font-medium text-gray-700">
								Customer
							</label>
							<select
								id="customer-select"
								v-model="selectedCustomerCode"
								@change="onCustomerChange"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option value="">Select a customer</option>
								<option v-for="code in customerCodes" :key="code" :value="code">
									{{ code }}
								</option>
							</select>
						</div>
					</div>
				</div>
			</div>

			<!-- Error -->
			<div v-if="error" class="mb-6 rounded-md border border-red-300 bg-red-50 p-4">
				<p class="text-sm text-red-700">{{ error }}</p>
			</div>

			<!-- Loading -->
			<div v-if="loading" class="rounded-lg bg-white px-4 py-12 text-center shadow">
				<div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-indigo-600"></div>
				<p class="mt-2 text-sm text-gray-500">Loading dashboards...</p>
			</div>

			<!-- Dashboards Table -->
			<div v-else-if="selectedCustomerCode">
				<div class="mb-4 flex items-center justify-between">
					<h2 class="text-lg font-medium text-gray-900">Enabled Dashboards</h2>
					<span class="text-sm text-gray-500">{{ dashboards.length }} dashboard(s)</span>
				</div>

				<div v-if="dashboards.length > 0" class="overflow-hidden rounded-lg bg-white shadow">
					<div class="overflow-x-auto">
						<table class="min-w-full divide-y divide-gray-200">
							<thead class="bg-gray-50">
								<tr>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Dashboard
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Category
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Template
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Created
									</th>
									<th
										class="px-6 py-3 text-right text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Action
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 bg-white">
								<tr v-for="dash in dashboards" :key="dash.id" class="hover:bg-gray-50">
									<td class="px-6 py-4 text-sm font-medium text-gray-900">
										{{ dash.display_name }}
									</td>
									<td class="px-6 py-4 text-sm text-gray-500">
										{{ dash.library_card }}
									</td>
									<td class="px-6 py-4 text-sm text-gray-500">
										{{ dash.template_id }}
									</td>
									<td class="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
										{{ formatDate(dash.created_at) }}
									</td>
									<td class="px-6 py-4 text-right text-sm whitespace-nowrap">
										<router-link
											:to="`/dashboards/view/${dash.id}`"
											class="font-medium text-indigo-600 hover:text-indigo-900"
										>
											View Dashboard
										</router-link>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>

				<!-- Empty State -->
				<div v-else class="rounded-lg bg-white px-4 py-12 text-center shadow">
					<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
						/>
					</svg>
					<h3 class="mt-2 text-sm font-medium text-gray-900">No dashboards enabled</h3>
					<p class="mt-1 text-sm text-gray-500">
						Contact your administrator to enable dashboards for your account.
					</p>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeMount } from "vue"
import { useRouter } from "vue-router"
import { usePortalSettingsStore } from "@/stores/portalSettings"
import { SiemAPI, type EnabledDashboard } from "@/api/siem"

const router = useRouter()
const portalSettingsStore = usePortalSettingsStore()

const showLogo = ref(true)
const error = ref("")
const loading = ref(false)

const username = computed(() => {
	try {
		const user = JSON.parse(localStorage.getItem("customer-portal-user") || "{}")
		return user.username || "User"
	} catch {
		return "User"
	}
})
const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

function logout() {
	localStorage.removeItem("customer-portal-auth-token")
	localStorage.removeItem("customer-portal-user")
	router.push("/login")
}

// -- Customer selection --
const customerCodes = ref<string[]>([])
const selectedCustomerCode = ref("")
const dashboards = ref<EnabledDashboard[]>([])

async function loadCustomerCodes() {
	try {
		const response = await SiemAPI.getCustomerCodes()
		customerCodes.value = response.customer_codes.filter(c => c !== "*")
		// Auto-select if only one customer
		if (customerCodes.value.length === 1) {
			selectedCustomerCode.value = customerCodes.value[0]
			loadDashboards(selectedCustomerCode.value)
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load customer codes"
	}
}

function onCustomerChange() {
	dashboards.value = []
	error.value = ""
	if (selectedCustomerCode.value) {
		loadDashboards(selectedCustomerCode.value)
	}
}

async function loadDashboards(customerCode: string) {
	loading.value = true
	try {
		const response = await SiemAPI.getEnabledDashboards(customerCode)
		dashboards.value = response.enabled_dashboards
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load dashboards"
	} finally {
		loading.value = false
	}
}

function formatDate(dateStr: string): string {
	try {
		return new Date(dateStr).toLocaleDateString()
	} catch {
		return dateStr
	}
}

onBeforeMount(() => {
	loadCustomerCodes()
})
</script>
