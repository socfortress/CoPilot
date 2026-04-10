<template>
	<div>
		<div>
			<Filters v-model:value="filters" />

			<!-- Alerts List -->
			<div class="overflow-hidden bg-white shadow sm:rounded-md">
				<div v-if="loading" class="px-4 py-5 text-center sm:p-6">
					<div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-indigo-600"></div>
					<p class="mt-2 text-sm text-gray-500">Loading alerts...</p>
				</div>

				<div v-else-if="error" class="px-4 py-5 text-center sm:p-6">
					<div class="mb-2 text-red-500">
						<svg class="mx-auto h-8 w-8" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
								clip-rule="evenodd"
							></path>
						</svg>
					</div>
					<p class="text-sm text-red-600">{{ error }}</p>
					<button
						class="mt-2 inline-flex items-center rounded-md border border-transparent bg-indigo-100 px-3 py-2 text-sm leading-4 font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
						@click="loadAlerts"
					>
						Try Again
					</button>
				</div>

				<ul v-else-if="alerts.length > 0" role="list" class="divide-y divide-gray-200">
					<li v-for="alert in alerts" :key="alert.id" class="px-4 py-4 hover:bg-gray-50 sm:px-6">
						<div class="flex items-center justify-between">
							<div class="flex items-center">
								<div class="shrink-0">
									<span
										class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': alert.status === 'OPEN',
											'bg-yellow-100 text-yellow-800': alert.status === 'IN_PROGRESS',
											'bg-green-100 text-green-800': alert.status === 'CLOSED'
										}"
									>
										{{ alert.status.replace("_", " ").toUpperCase() }}
									</span>
								</div>
								<div class="ml-4">
									<div class="text-sm font-medium text-gray-900">
										{{ alert.alert_name }}
									</div>
									<div class="text-sm text-gray-500">
										<span v-if="alert.assets.length > 0">
											Asset: {{ alert.assets[0].asset_name }}
										</span>
										<span v-else-if="alert.asset_name">Asset: {{ alert.asset_name }}</span>
										| Source: {{ alert.source }}
									</div>
									<div class="text-xs text-gray-400">
										{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
									</div>
								</div>
							</div>
							<div class="flex items-center space-x-2">
								<select
									:value="alert.status"
									class="rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
									:disabled="updatingStatus === alert.id"
									@change="updateAlertStatus(alert.id, ($event.target as HTMLSelectElement).value)"
								>
									<option value="OPEN">Open</option>
									<option value="IN_PROGRESS">In Progress</option>
									<option value="CLOSED">Closed</option>
								</select>
								<button
									class="inline-flex items-center rounded border border-transparent bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
									@click="viewAlert(alert.id)"
								>
									View Details
								</button>
							</div>
						</div>
						<div v-if="alert.alert_description" class="mt-2 text-sm text-gray-600">
							{{ alert.alert_description }}
						</div>
					</li>
				</ul>

				<div v-else class="px-4 py-5 text-center sm:p-6">
					<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
						></path>
					</svg>
					<h3 class="mt-2 text-sm font-medium text-gray-900">No alerts found</h3>
					<p class="mt-1 text-sm text-gray-500">No security alerts match your current filters.</p>
				</div>
			</div>

			<!-- Pagination -->
			<div class="mt-6 flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
				<div class="flex flex-1 justify-between sm:hidden">
					<button
						:disabled="currentPage <= 1"
						class="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
						@click="previousPage"
					>
						Previous
					</button>
					<button
						:disabled="currentPage >= totalPages"
						class="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
						@click="nextPage"
					>
						Next
					</button>
				</div>
				<div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
					<div>
						<p class="text-sm text-gray-700">
							Showing
							<span class="font-medium">{{ (currentPage - 1) * pageSize + 1 }}</span>
							to
							<span class="font-medium">{{ Math.min(currentPage * pageSize, totalItems) }}</span>
							of
							<span class="font-medium">{{ totalItems }}</span>
							results
						</p>
					</div>
					<div>
						<nav class="relative z-0 inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
							<button
								:disabled="currentPage <= 1"
								class="relative inline-flex items-center rounded-l-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
								@click="previousPage"
							>
								Previous
							</button>
							<button
								:disabled="currentPage >= totalPages"
								class="relative inline-flex items-center rounded-r-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
								@click="nextPage"
							>
								Next
							</button>
						</nav>
					</div>
				</div>
			</div>
		</div>

		<AlertDetailsModal :alert-id="selectedAlertId" @close="closeModal" />
	</div>
</template>

<script setup lang="ts">
import type { AxiosResponse } from "axios"
import type { Alert, AlertsListResponse, AlertStatus } from "@/api/endpoints/alerts"
import type { FiltersModel } from "@/components/alerts/Filters.vue"
import type { ApiError, CommonResponse, Pagination } from "@/types/common"
import { watchDebounced } from "@vueuse/core"
import { useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import AlertDetailsModal from "@/components/alerts/AlertDetailsModal.vue"
import Filters from "@/components/alerts/Filters.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const message = useMessage()
// Reactive data
const alerts = ref<Alert[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedAlertId = ref<number | null>(null)
const updatingStatus = ref<number | null>(null)
const dFormats = useSettingsStore().dateFormat
const totalItems = ref(0)

// Pagination
const currentPage = ref(1)
const pageSize = ref(25)

// Filters
const filters = ref<FiltersModel>({
	key: null,
	value: null
})

const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value))

async function loadAlerts() {
	loading.value = true
	error.value = null

	try {
		let response: AxiosResponse<CommonResponse<AlertsListResponse>>

		const pagination: Pagination = {
			page: currentPage.value,
			pageSize: pageSize.value,
			order: "desc"
		}

		if (filters.value.key && filters.value.value) {
			switch (filters.value.key) {
				case "status":
					response = await Api.alerts.getAlertsByStatus(filters.value.value as AlertStatus, pagination)
					break
				case "source":
					response = await Api.alerts.getAlertsBySource(filters.value.value, pagination)
					break
				case "asset":
					response = await Api.alerts.getAlertsByAsset(filters.value.value, pagination)
					break
				default:
					response = await Api.alerts.getAlerts(pagination)
					break
			}
		} else {
			response = await Api.alerts.getAlerts(pagination)
		}

		alerts.value = response.data.alerts
		totalItems.value = response.data.total
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

function applyFilters() {
	currentPage.value = 1
	loadAlerts()
}

watchDebounced(
	filters,
	() => {
		applyFilters()
	},
	{ deep: true, immediate: true, debounce: 300 }
)

async function updateAlertStatus(alertId: number, newStatus: string) {
	updatingStatus.value = alertId

	try {
		await Api.alerts.updateAlertStatus(alertId, newStatus as AlertStatus)

		// Update the local alert status
		const alert = alerts.value.find(a => a.id === alertId)
		if (alert) {
			alert.status = newStatus as AlertStatus
		}

		// Refresh stats
		await loadAlerts()
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to update alert status"
		console.error("Error updating alert status:", err)
	} finally {
		updatingStatus.value = null
	}
}

function viewAlert(alertId: number) {
	selectedAlertId.value = alertId
}

function closeModal() {
	selectedAlertId.value = null
}

function previousPage() {
	if (currentPage.value > 1) {
		currentPage.value--
		loadAlerts()
	}
}

function nextPage() {
	if (currentPage.value < totalPages.value) {
		currentPage.value++
		loadAlerts()
	}
}
</script>
