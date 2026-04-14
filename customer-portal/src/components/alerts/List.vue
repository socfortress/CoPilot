<template>
	<div>
		<div class="flex flex-col gap-4">
			<div>
				<Filters v-model:value="filters" class="w-auto!" />
			</div>

			<div class="flex flex-col gap-2">
				<div ref="headerRef" class="flex items-center justify-between">
					<Chip size="small" :value="loading ? 'Loading...' : pagination.total" label="items" />

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
						:scroll-x="1400"
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
	</div>
</template>

<script setup lang="tsx">
import type { AxiosResponse } from "axios"
import type { DataTableColumns } from "naive-ui"
import type { AlertStatusUpdateSuccessPayload } from "@/components/alerts/AlertStatusSelect.vue"
import type { FiltersModel } from "@/components/alerts/Filters.vue"
import type { Alert, AlertsListResponse, AlertStatus } from "@/types/alerts"
import type { ApiError, CommonResponse, Pagination } from "@/types/common"
import { useDebounceFn, useElementSize, watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NDataTable, NEmpty, NPagination, NTag, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
import Api from "@/api"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import AlertStatusSelect from "@/components/alerts/AlertStatusSelect.vue"
import Filters from "@/components/alerts/Filters.vue"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"

const message = useMessage()
const data = ref<Alert[]>([])
const loading = ref(false)
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

const columns = computed<DataTableColumns<Alert>>(() => [
	{
		title: "Alert",
		key: "alert",
		fixed: simpleMode.value ? undefined : "left",
		width: 380,
		render: row => <div>{row.alert_name}</div>
	},
	{
		title: "Source",
		key: "source",
		width: 180,
		render: row => <div>{row.source}</div>
	},
	{
		title: "Assets",
		key: "assets",
		width: "100%",
		render: row => <div>{row.assets.map(asset => asset.asset_name).join(", ")}</div>
	},
	{
		title: "Created",
		key: "alert_creation_time",
		width: 200,
		render: row => <span class="font-mono text-sm">{formatDate(row.alert_creation_time, dFormats.datetime)}</span>
	},
	{
		title: "Status",
		key: "status",
		width: 120,
		render: row => {
			return (
				<div class="flex items-center gap-2">
					<NTag
						type={getStatusColor(row.status)}
						round
						class="p-1! [&_.n-tag\_\_icon]:m-0!"
						v-slots={{
							icon: () => <Icon name="carbon:circle-solid" />
						}}
					/>
					<AlertStatusSelect alertId={row.id} status={row.status} onSuccess={handleStatusUpdateSuccess} />
				</div>
			)
		}
	},
	{
		title: "Actions",
		key: "actions",
		minWidth: 180,
		render: row => {
			return <AlertDetailsButton alertId={row.id} onStatusUpdated={handleStatusUpdateSuccess} />
		}
	}
])

let abortController = new AbortController()

const loadAlerts = useDebounceFn(async () => {
	loading.value = true

	abortController?.abort()
	abortController = new AbortController()

	try {
		let response: AxiosResponse<CommonResponse<AlertsListResponse>>

		const paginationPayload: Pagination = {
			page: pagination.value.page,
			pageSize: pagination.value.pageSize,
			order: "desc"
		}

		if (filters.value.key && filters.value.value) {
			switch (filters.value.key) {
				case "statuses":
					response = await Api.alerts.getAlertsByStatus(
						filters.value.value as AlertStatus,
						paginationPayload,
						abortController.signal
					)
					break
				case "sources":
					response = await Api.alerts.getAlertsBySource(
						filters.value.value,
						paginationPayload,
						abortController.signal
					)
					break
				case "assets":
					response = await Api.alerts.getAlertsByAsset(
						filters.value.value,
						paginationPayload,
						abortController.signal
					)
					break
				case "tags":
					response = await Api.alerts.getAlertsByTag(
						filters.value.value,
						paginationPayload,
						abortController.signal
					)
					break
				default:
					response = await Api.alerts.getAlerts(paginationPayload, abortController.signal)
					break
			}
		} else {
			response = await Api.alerts.getAlerts(paginationPayload, abortController.signal)
		}

		data.value = response.data.alerts
		pagination.value.total = response.data.total
		loading.value = false
	} catch (err) {
		if (!axios.isCancel(err)) {
			message.error(getApiErrorMessage(err as ApiError))
			loading.value = false
		}
	}
}, 400)

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
	const alert = data.value.find(a => a.id === payload.alertId)
	if (alert) {
		alert.status = payload.status
	}
}

watchDebounced([() => pagination.value.page, () => pagination.value.pageSize], loadAlerts, {
	deep: true,
	immediate: true,
	debounce: 300
})
</script>
