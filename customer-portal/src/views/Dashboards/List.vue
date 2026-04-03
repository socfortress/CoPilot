<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Main Content -->
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
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
											:to="{ name: 'DashboardView', params: { id: dash.id } }"
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
import type { EnabledDashboard } from "@/api/endpoints/siem"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"

const error = ref("")
const loading = ref(false)

// -- Customer selection --
const customerCodes = ref<string[]>([])
const selectedCustomerCode = ref("")
const dashboards = ref<EnabledDashboard[]>([])

// TODO-FE: CP get customer code from login
async function loadCustomerCodes() {
	try {
		const response = await Api.siem.getCustomerCodes()
		customerCodes.value = response.data.customer_codes.filter(c => c !== "*")
		// Auto-select if only one customer
		if (customerCodes.value.length) {
			selectedCustomerCode.value = customerCodes.value[0]
			loadDashboards(selectedCustomerCode.value)
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load customer codes"
	}
}

async function loadDashboards(customerCode: string) {
	loading.value = true
	try {
		const response = await Api.siem.getEnabledDashboards(customerCode)
		dashboards.value = response.data.enabled_dashboards
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
