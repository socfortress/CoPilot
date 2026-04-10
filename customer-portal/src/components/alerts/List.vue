<template>
	<div>
		<div>
			<Filters v-model:value="filters" />

			<div class="flex flex-col gap-2">
				<div ref="headerRef" class="flex items-center justify-between">
					<n-tag size="small">
						<div :class="{ 'font-mono': !loading }">
							{{ loading ? "Loading..." : pagination.total }}
						</div>
						<div class="text-secondary">items</div>
					</n-tag>

					<div class="flex items-center gap-2 whitespace-nowrap">
						<n-pagination
							v-model:page="pagination.page"
							v-model:page-size="pagination.pageSize"
							:page-slot
							:show-size-picker
							:page-sizes
							:item-count="pagination.total"
							:simple="simpleMode"
							size="small"
						/>
					</div>
				</div>

				<div class="grow overflow-hidden">
					<n-data-table
						bordered
						:loading
						size="small"
						:data
						:columns
						:scroll-x="2200"
						class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
					>
						<template #empty>
							<n-empty description="No alerts found">
								<template #extra>try changing the filters</template>
							</n-empty>
						</template>
					</n-data-table>
				</div>

				<div class="flex justify-end">
					<n-pagination
						v-if="data.length > 3"
						v-model:page="pagination.page"
						:page-size="pagination.pageSize"
						:item-count="pagination.total"
						:page-slot="6"
						size="small"
						:simple="simpleMode"
					/>
				</div>
			</div>
		</div>

		<AlertDetailsModal :alert-id="selectedAlertId" @close="closeModal" />
	</div>
</template>

<script setup lang="tsx">
import type { AxiosResponse } from "axios"
import type { DataTableColumns } from "naive-ui"
import type { Alert, AlertsListResponse, AlertStatus } from "@/api/endpoints/alerts"
import type {
	AlertStatusUpdateErrorPayload,
	AlertStatusUpdateSuccessPayload
} from "@/components/alerts/AlertStatusSelect.vue"
import type { FiltersModel } from "@/components/alerts/Filters.vue"
import type { ApiError, CommonResponse, Pagination } from "@/types/common"
import { useElementSize, watchDebounced } from "@vueuse/core"
import { NDataTable, NEmpty, NPagination, NTag, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
import Api from "@/api"
import AlertDetailsModal from "@/components/alerts/AlertDetailsModal.vue"
import AlertStatusSelect from "@/components/alerts/AlertStatusSelect.vue"
import Filters from "@/components/alerts/Filters.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const message = useMessage()
// Reactive data
const data = ref<Alert[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedAlertId = ref<number | null>(null)
const dFormats = useSettingsStore().dateFormat

const { width: headerWidthRef } = useElementSize(useTemplateRef("headerRef"))
const pageSizes = [10, 25, 50, 100]
const pageSlot = computed(() => (headerWidthRef.value < 800 ? 5 : 8))
const simpleMode = computed(() => headerWidthRef.value < 600)
const showSizePicker = ref(true)

const pagination = ref({
	page: 1,
	pageSize: pageSizes[1],
	total: 0
})

// Filters
const filters = ref<FiltersModel>({
	key: null,
	value: null
})

// const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.pageSize))

const columns = computed<DataTableColumns<Alert>>(() => [
	{
		title: "Alert",
		key: "alert",
		fixed: simpleMode.value ? undefined : "left",
		width: 280,
		render: row => <div>{row.alert_name}</div>
	},
	{
		title: "Assets",
		key: "assets",
		width: 180,
		render: row => <div>{row.assets.map(asset => asset.asset_name).join(", ")}</div>
	},
	{
		title: "Source",
		key: "source",
		minWidth: 400,
		render: row => <div>{row.source}</div>
	},
	{
		title: "Created",
		key: "alert_creation_time",
		width: 100,
		render: row => <span class="font-mono text-sm">{formatDate(row.alert_creation_time, dFormats.datetime)}</span>
	},
	{
		title: "Status",
		key: "status",
		width: 120,
		render: row => {
			return (
				<AlertStatusSelect
					alertId={row.id}
					status={row.status}
					onSuccess={(payload: AlertStatusUpdateSuccessPayload) => handleStatusUpdateSuccess(payload)}
					onError={(payload: AlertStatusUpdateErrorPayload) => handleStatusUpdateError(payload)}
				/>
			)
		}
	},
	{
		title: "Actions",
		key: "actions",
		minWidth: 180,
		render: row => (
			<button
				class="inline-flex items-center rounded border border-transparent bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
				onClick={() => viewAlert(row.id)}
			>
				View Details
			</button>
		)
	}
])

async function loadAlerts() {
	loading.value = true
	error.value = null

	try {
		let response: AxiosResponse<CommonResponse<AlertsListResponse>>

		const paginationPayload: Pagination = {
			page: pagination.value.page,
			pageSize: pagination.value.pageSize,
			order: "desc"
		}

		if (filters.value.key && filters.value.value) {
			switch (filters.value.key) {
				case "status":
					response = await Api.alerts.getAlertsByStatus(filters.value.value as AlertStatus, paginationPayload)
					break
				case "source":
					response = await Api.alerts.getAlertsBySource(filters.value.value, paginationPayload)
					break
				case "asset":
					response = await Api.alerts.getAlertsByAsset(filters.value.value, paginationPayload)
					break
				default:
					response = await Api.alerts.getAlerts(paginationPayload)
					break
			}
		} else {
			response = await Api.alerts.getAlerts(paginationPayload)
		}

		data.value = response.data.alerts
		pagination.value.total = response.data.total
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

function applyFilters() {
	pagination.value.page = 1
	loadAlerts()
}

watchDebounced(
	() => filters.value.value,
	() => {
		applyFilters()
	},
	{ deep: true, immediate: true, debounce: 300 }
)

function handleStatusUpdateSuccess(payload: AlertStatusUpdateSuccessPayload) {
	message.success(`Alert status updated to ${payload.status}`)
	const alert = data.value.find(a => a.id === payload.alertId)
	if (alert) {
		alert.status = payload.status
	}
}

function handleStatusUpdateError(payload: AlertStatusUpdateErrorPayload) {
	message.error(payload.message)
}

function viewAlert(alertId: number) {
	selectedAlertId.value = alertId
}

function closeModal() {
	selectedAlertId.value = null
}

watchDebounced([() => pagination.value.page, () => pagination.value.pageSize], loadAlerts, {
	deep: true,
	immediate: true,
	debounce: 300
})
</script>
