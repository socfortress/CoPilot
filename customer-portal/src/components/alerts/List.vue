<template>
	<div class="flex flex-col gap-4">
		<AlertsFilterBar :filters @change="patch => emit('change', patch)" />

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
					data-testid="alerts-table"
					bordered
					:loading
					size="small"
					:data
					:columns
					:scroll-x="1600"
					class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
				>
					<template #empty>
						<n-empty description="No alerts found">
							<template v-if="hasFilters(filters)" #extra>
								<n-button
									size="small"
									data-testid="alerts-empty-clear"
									@click="emit('change', EMPTY_ALERTS_FILTERS)"
								>
									Clear filters
								</n-button>
							</template>
						</n-empty>
					</template>
				</n-data-table>
			</div>

			<div class="flex justify-end">
				<n-pagination
					v-if="pagination.total > pagination.pageSize"
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
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { AlertStatusUpdateSuccessPayload } from "@/components/alerts/AlertStatusSelect.vue"
import type { AlertsFilters } from "@/components/alerts/filters/alertsFilters"
import type { Alert } from "@/types/alerts"
import type { ApiError, Pagination } from "@/types/common"
import { useElementSize } from "@vueuse/core"
import { NButton, NDataTable, NEmpty, NPagination, NTag, useMessage } from "naive-ui"
import { computed, ref, toRef, useTemplateRef } from "vue"
import Api from "@/api"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import AlertStatusSelect from "@/components/alerts/AlertStatusSelect.vue"
import AlertsFilterBar from "@/components/alerts/filters/AlertsFilterBar.vue"
import {
	EMPTY_ALERTS_FILTERS,
	filtersKey,
	filtersToParams,
	hasFilters
} from "@/components/alerts/filters/alertsFilters"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { usePaginatedLoad } from "@/composables/common/usePaginatedLoad"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, statusTagProps } from "@/utils"
import { formatDate } from "@/utils/format"

// The filters live in the URL, owned by the page (it shares them with the status cards).
const { filters } = defineProps<{ filters: AlertsFilters }>()

const emit = defineEmits<{
	(e: "change", patch: Partial<AlertsFilters>): void
}>()

const message = useMessage()
const { loading, run } = useLatestRequest()
const data = ref<Alert[]>([])
const dFormats = useSettingsStore().dateFormat
const customerFilterStore = useCustomerFilterStore()

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
		ellipsis: true,
		render: row => row.assets.map(asset => asset.asset_name).join(", ")
	},
	{
		// Shown because they can be filtered on: a match must be explainable from the row.
		title: "Tags",
		key: "tags",
		width: 200,
		render: row => (
			<div class="flex flex-wrap gap-1" data-testid="alert-tags">
				{row.tags.map(tag => (
					<NTag key={tag.id} size="small" bordered={false}>
						{tag.tag}
					</NTag>
				))}
			</div>
		)
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
		width: 200,
		render: row => {
			return (
				<div class="flex items-center gap-2">
					<NTag
						{...statusTagProps(row.status)}
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
		width: 194,
		render: row => {
			return <AlertDetailsButton alertId={row.id} onStatusUpdated={handleStatusUpdateSuccess} />
		}
	}
])

function loadAlerts() {
	return run(
		async signal => {
			const paginationPayload: Pagination = {
				page: pagination.value.page,
				pageSize: pagination.value.pageSize,
				order: "desc"
			}
			const response = await Api.alerts.getFilteredAlerts(
				filtersToParams(filters),
				paginationPayload,
				signal,
				customerFilterStore.queryCustomerCodes
			)
			data.value = response.data.alerts
			pagination.value.total = response.data.total_filtered
		},
		err => message.error(getApiErrorMessage(err as ApiError))
	)
}

function handleStatusUpdateSuccess(payload: AlertStatusUpdateSuccessPayload) {
	const alert = data.value.find(a => a.id === payload.alertId)
	if (alert) {
		alert.status = payload.status
	}
}

usePaginatedLoad({
	page: toRef(pagination.value, "page"),
	// The filters by what they ask, not by object: an unrelated query change rebuilds them.
	resetOn: [() => pagination.value.pageSize, () => filtersKey(filters), () => customerFilterStore.queryCustomerCodes],
	load: loadAlerts
})
</script>
