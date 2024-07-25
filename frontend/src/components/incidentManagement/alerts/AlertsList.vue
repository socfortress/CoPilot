<template>
	<div class="alerts-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total :
							<code>{{ total }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="total"
				:simple="simpleMode"
			/>
			<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="!px-0">
				<template #trigger>
					<div class="bg-color border-radius">
						<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon"></Icon>
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<div class="py-1 flex flex-col gap-2">
					<div class="px-3">
						<n-input-group>
							<n-select
								v-model:value="filters.type"
								:options="typeOptions"
								placeholder="Filter by..."
								clearable
								class="!w-36"
							/>

							<n-select
								v-if="filters.type === 'status'"
								v-model:value="filters.value"
								:options="statusOptions"
								placeholder="Value..."
								clearable
								class="!w-56"
							/>
							<n-input
								v-else
								v-model:value="filters.value"
								placeholder="Value..."
								clearable
								class="!w-56"
							/>
						</n-input-group>
					</div>
					<div class="px-3 flex justify-end gap-2">
						<n-button size="small" @click="showFilters = false" secondary>Close</n-button>
						<n-button size="small" @click="getData()" type="primary" secondary :loading>Submit</n-button>
					</div>
				</div>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="list flex flex-col gap-2 my-3">
				<template v-if="alertsList.length">
					<pre
						v-for="alert of itemsPaginated"
						:key="alert.id"
						class="item-appear item-appear-bottom item-appear-005"
						>{{ alert }}</pre
					>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="itemsPaginated.length > 3"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, watch } from "vue"
import {
	useMessage,
	NSpin,
	NPopover,
	NButton,
	NEmpty,
	NSelect,
	NPagination,
	NInputGroup,
	NBadge,
	NInput
} from "naive-ui"
import Api from "@/api"
import _cloneDeep from "lodash/cloneDeep"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import type { Alert, AlertStatus } from "@/types/incidentManagement/alerts.d"
import type { AlertsFilter } from "@/api/endpoints/incidentManagement"

export interface AlertsListFilter {
	type: "status" | "assetName" | "assignedTo"
	value: string | AlertStatus
}

const message = useMessage()
const loading = ref(false)
const showFilters = ref(false)
const alertsList = ref<Alert[]>([])

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	return alertsList.value.slice(from, to)
})

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return alertsList.value.length || 0
})

const filters = ref<Partial<AlertsListFilter>>({})
const lastFilters = ref<Partial<AlertsListFilter>>({})

const filtered = computed<boolean>(() => {
	return !!filters.value.type && !!filters.value.value
})

const typeOptions = [
	{ label: "Status", value: "status" },
	{ label: "Asset Name", value: "assetName" },
	{ label: "Assigned To", value: "assignedTo" }
]

const statusOptions = [
	{ label: "Open", value: "OPEN" },
	{ label: "Closed", value: "CLOSED" },
	{ label: "In progress", value: "IN_PROGRESS" }
]

watch(showFilters, val => {
	if (!val) {
		filters.value = _cloneDeep(lastFilters.value)
	}
})

watch(
	() => filters.value.type,
	() => {
		filters.value.value = undefined
	}
)

function getData() {
	showFilters.value = false
	loading.value = true

	lastFilters.value = _cloneDeep(filters.value)

	let query: AlertsFilter | undefined = undefined
	if (filtered.value) {
		// @ts-expect-error filters properties infer are ignored
		query = { [filters.value.type]: filters.value.value }
	}

	Api.incidentManagement
		.getAlertsList(query)
		.then(res => {
			if (res.data.success) {
				alertsList.value = res.data?.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			alertsList.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.alerts-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
