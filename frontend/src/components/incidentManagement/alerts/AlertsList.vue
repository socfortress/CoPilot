<template>
	<div class="alerts-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-2 lg:!hidden">
				<n-popover overlap placement="left">
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
						<div class="box text-error-color">
							Open :
							<code>{{ statusOpenTotal }}</code>
						</div>
						<div class="box text-warning-color">
							In Progress :
							<code>{{ statusInProgressTotal }}</code>
						</div>
						<div class="box text-success-color">
							Close :
							<code>{{ statusCloseTotal }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="info grow lg:flex gap-2 hidden text-sm">
				Total :
				<code>{{ total }}</code>
				<span>/</span>
				<span class="text-secondary-color">Open :</span>
				<code class="text-error-color">{{ statusOpenTotal }}</code>
				<span>/</span>
				<span class="text-secondary-color">In Progress :</span>
				<code class="text-warning-color">{{ statusInProgressTotal }}</code>
				<span>/</span>
				<span class="text-secondary-color">Close :</span>
				<code class="text-success-color">{{ statusCloseTotal }}</code>
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
			<n-select
				size="small"
				v-model:value="sort"
				:options="sortOptions"
				:show-checkmark="false"
				class="max-w-20"
				:disabled="loading"
			/>
			<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="!px-0" v-if="!hideFilters">
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
								:disabled="!filters.type"
								clearable
								class="!w-56"
							/>
							<n-select
								v-else-if="filters.type === 'assignedTo'"
								v-model:value="filters.value"
								:options="usersOptions"
								placeholder="Value..."
								:disabled="!filters.type"
								clearable
								class="!w-56"
							/>
							<n-input
								v-else
								v-model:value="filters.value"
								placeholder="Value..."
								:disabled="!filters.type"
								clearable
								class="!w-56"
							/>
						</n-input-group>
					</div>
					<div class="px-3 flex justify-between gap-2">
						<div class="flex justify-start gap-2">
							<n-button size="small" @click="showFilters = false" quaternary>Close</n-button>
						</div>
						<div class="flex justify-end gap-2">
							<n-button size="small" @click="resetFilters()" secondary>Reset</n-button>
							<n-button size="small" @click="getData()" type="primary" secondary :loading>
								Submit
							</n-button>
						</div>
					</div>
				</div>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="list flex flex-col gap-2 my-3">
				<template v-if="alertsList.length">
					<AlertItem
						v-for="alert of alertsList"
						:key="alert.id"
						:alertData="alert"
						:highlight="highlight === alert.id.toString()"
						:detailsOnMounted="highlight === alert.id.toString() && !highlightedItemOpened"
						class="item-appear item-appear-bottom item-appear-005"
						@opened="highlightedItemOpened = true"
						@deleted="getData()"
						@updated="updateAlert($event)"
					/>
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
				v-if="alertsList.length > 3"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, watch, provide, toRefs, nextTick } from "vue"
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
import AlertItem from "./AlertItem.vue"
import Icon from "@/components/common/Icon.vue"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import axios from "axios"
import { useResizeObserver } from "@vueuse/core"
import type { Alert, AlertStatus } from "@/types/incidentManagement/alerts.d"
import type { AlertsQuery } from "@/api/endpoints/incidentManagement"
import type { Case } from "@/types/incidentManagement/cases.d"

export interface AlertsListFilter {
	type: "status" | "assetName" | "assignedTo" | "tag" | "title"
	value: string | AlertStatus
}

const props = defineProps<{ highlight?: string | null; preset?: AlertsListFilter; hideFilters?: boolean }>()
const { highlight, preset, hideFilters } = toRefs(props)

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const showFilters = ref(false)
const alertsList = ref<Alert[]>([])
const availableUsers = ref<string[]>([])
const linkableCases = ref<Case[]>([])
let abortController: AbortController | null = null

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)
const sort = defineModel<"asc" | "desc">("sort", { default: "desc" })
const sortOptions = [
	{ label: "Desc", value: "desc" },
	{ label: "Asc", value: "asc" }
]

const total = ref(0)
const statusOpenTotal = ref(0)
const statusInProgressTotal = ref(0)
const statusCloseTotal = ref(0)

const filters = ref<Partial<AlertsListFilter>>({})
const lastFilters = ref<Partial<AlertsListFilter>>({})

const filtered = computed<boolean>(() => {
	return !!filters.value.type && !!filters.value.value
})

const typeOptions = [
	{ label: "Status", value: "status" },
	{ label: "Asset Name", value: "assetName" },
	{ label: "Assigned To", value: "assignedTo" },
	{ label: "Tag", value: "tag" },
	{ label: "Title", value: "title" }
]

const statusOptions: { label: string; value: AlertStatus }[] = [
	{ label: "Open", value: "OPEN" },
	{ label: "Closed", value: "CLOSED" },
	{ label: "In progress", value: "IN_PROGRESS" }
]

const usersOptions = computed(() => availableUsers.value.map(o => ({ label: o, value: o })))

const highlightedItemFound = ref(!highlight.value)
const highlightedItemOpened = ref(!highlight.value)

watch(showFilters, val => {
	if (!val) {
		filters.value = _cloneDeep(lastFilters.value)
	}
})

watch(
	() => filters.value.type,
	() => {
		if (!preset.value) {
			filters.value.value = undefined
		}
	}
)

watch([currentPage, sort], () => {
	getData()
})

watch(pageSize, () => {
	if (currentPage.value === 1) {
		getData()
	} else {
		currentPage.value = 1
	}
})

watch(
	alertsList,
	() => {
		if (
			alertsList.value.length &&
			!alertsList.value.find(o => o.id.toString() === highlight.value) &&
			currentPage.value < total.value &&
			!highlightedItemFound.value
		) {
			nextTick(() => {
				currentPage.value++
			})
		}

		if (alertsList.value.find(o => o.id.toString() === highlight.value)) {
			highlightedItemFound.value = true
		}
	},
	{ immediate: true }
)

provide("assignable-users", availableUsers)

provide("linkable-cases", linkableCases)

function resetFilters() {
	filters.value.type = undefined
	filters.value.value = undefined
	showFilters.value = false
	getData()
}

function updateAlert(updatedAlert: Alert) {
	const alertIndex = alertsList.value.findIndex(o => o.id === updatedAlert.id)
	if (alertIndex !== -1) {
		alertsList.value[alertIndex] = updatedAlert
	}
}

function getData() {
	abortController?.abort()
	abortController = new AbortController()

	showFilters.value = false
	loading.value = true
	lastFilters.value = _cloneDeep(filters.value)

	const query: Partial<AlertsQuery> = {
		page: currentPage.value,
		pageSize: pageSize.value,
		sort: sort.value
	}

	if (filtered.value) {
		// @ts-expect-error filters properties infer are ignored
		query.filters = { [filters.value.type]: filters.value.value }
	}

	Api.incidentManagement
		.getAlertsList(query, abortController.signal)
		.then(res => {
			if (res.data.success) {
				alertsList.value = res.data?.alerts || []
				total.value = res.data.total || 0
				statusCloseTotal.value = res.data.closed || 0
				statusInProgressTotal.value = res.data.in_progress || 0
				statusOpenTotal.value = res.data.open || 0
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
			loading.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				alertsList.value = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loading.value = false
			}
		})
}

function getAvailableUsers() {
	Api.incidentManagement
		.getAvailableUsers()
		.then(res => {
			if (res.data.success) {
				availableUsers.value = res.data?.available_users || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
}

function getCases() {
	Api.incidentManagement
		.getCasesList()
		.then(res => {
			if (res.data.success) {
				linkableCases.value = _orderBy(res.data?.cases || [], ["id"], ["desc"])
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

onBeforeMount(() => {
	if (preset.value?.type && preset.value.value) {
		filters.value.type = preset.value.type
		filters.value.value = preset.value.value
	}

	getData()
	getAvailableUsers()
	getCases()
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
