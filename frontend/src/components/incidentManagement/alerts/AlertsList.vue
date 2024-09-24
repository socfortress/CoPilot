<template>
	<div class="alerts-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
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
			<div class="info grow lg:flex gap-1 hidden text-sm items-center">
				<n-button quaternary size="small" @click="filtersCTX?.setFilter([{ type: 'status', value: null }])">
					<div class="flex items-center gap-2">
						<span>Total</span>
						<code class="py-1">{{ total }}</code>
					</div>
				</n-button>
				<span>/</span>
				<n-button quaternary size="small" @click="filtersCTX?.setFilter([{ type: 'status', value: 'OPEN' }])">
					<div class="flex items-center gap-2">
						<span>Open</span>
						<code class="py-1 text-error-color">{{ statusOpenTotal }}</code>
					</div>
				</n-button>
				<span>/</span>
				<n-button
					quaternary
					size="small"
					@click="filtersCTX?.setFilter([{ type: 'status', value: 'IN_PROGRESS' }])"
				>
					<div class="flex items-center gap-2">
						<span>In Progress</span>
						<code class="py-1 text-warning-color">{{ statusInProgressTotal }}</code>
					</div>
				</n-button>
				<span>/</span>
				<n-button quaternary size="small" @click="filtersCTX?.setFilter([{ type: 'status', value: 'CLOSED' }])">
					<div class="flex items-center gap-2">
						<span>Close</span>
						<code class="py-1 text-success-color">{{ statusCloseTotal }}</code>
					</div>
				</n-button>
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
				v-model:value="sort"
				size="small"
				:options="sortOptions"
				:show-checkmark="false"
				class="max-w-20"
				:disabled="loading"
			/>

			<n-badge v-if="showFilters" :show="filtered" dot type="success" :offset="[-4, 0]">
				<n-button size="small" secondary @click="showFiltersView = !showFiltersView">
					<template #icon>
						<Icon :name="FilterIcon"></Icon>
					</template>
				</n-button>
			</n-badge>
		</div>

		<div v-if="showFilters" class="filters-box" :class="{ open: showFiltersView }">
			<n-card size="small" :bordered="false">
				<AlertsFilters
					:use-query-string="!preset?.length"
					:preset
					@submit="applyFilters"
					@mounted="filtersCTX = $event"
				/>
			</n-card>
		</div>

		<n-spin :show="loading">
			<div class="list flex flex-col gap-2 my-3">
				<template v-if="alertsList.length">
					<AlertItem
						v-for="alert of alertsList"
						:key="alert.id"
						:alert-data="alert"
						:highlight="highlight === alert.id.toString()"
						:details-on-mounted="highlight === alert.id.toString() && !highlightedItemOpened"
						class="item-appear item-appear-bottom item-appear-005"
						@opened="highlightedItemOpened = true"
						@deleted="getData()"
						@updated="updateAlert($event)"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="justify-center h-48" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-if="alertsList.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AlertsQuery } from "@/api/endpoints/incidentManagement"
import type { Alert } from "@/types/incidentManagement/alerts.d"
import type { Case } from "@/types/incidentManagement/cases.d"
import type { AlertsListFilter } from "./types.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver, useStorage } from "@vueuse/core"
import axios from "axios"
import _orderBy from "lodash/orderBy"
import { NBadge, NButton, NCard, NEmpty, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeMount, provide, ref, watch } from "vue"
import AlertItem from "./AlertItem.vue"
import AlertsFilters from "./AlertsFilters.vue"

const { highlight, preset, showFilters } = withDefaults(
	defineProps<{
		highlight?: string | null
		preset?: AlertsListFilter[]
		showFilters?: boolean
	}>(),
	{ showFilters: true }
)

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const showFiltersView = useStorage<boolean>("incident-management-alerts-list-filters-view-state", false, localStorage)
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

const filtersCTX = ref<{ setFilter: (payload: AlertsListFilter[]) => void } | null>(null)
const filters = ref<AlertsListFilter[]>([])

const filtered = computed<boolean>(() => {
	return !!filters.value.length
})

const highlightedItemFound = ref(!highlight)
const highlightedItemOpened = ref(!highlight)

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
			!alertsList.value.find(o => o.id.toString() === highlight) &&
			currentPage.value < total.value &&
			!highlightedItemFound.value
		) {
			nextTick(() => {
				currentPage.value++
			})
		}

		if (alertsList.value.find(o => o.id.toString() === highlight)) {
			highlightedItemFound.value = true
		}
	},
	{ immediate: true }
)

provide("assignable-users", availableUsers)

provide("linkable-cases", linkableCases)

function applyFilters(newFilters: AlertsListFilter[]) {
	filters.value = newFilters
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

	loading.value = true

	const query: Partial<AlertsQuery> = {
		page: currentPage.value,
		pageSize: pageSize.value,
		sort: sort.value
	}

	if (filtered.value) {
		query.filters = filters.value
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
	if (!showFilters && preset?.length) {
		filters.value = preset
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

	.filters-box {
		overflow: hidden;
		display: grid;
		grid-template-rows: 0fr;
		padding-top: 0px;
		opacity: 0;
		position: relative;
		transition:
			opacity var(--router-transition-duration) ease-out,
			grid-template-rows var(--router-transition-duration) ease-out,
			padding-top var(--router-transition-duration) ease-out;

		&::after {
			--size: 10px;
			content: "";
			width: 0;
			height: 0;
			border-left: var(--size) solid transparent;
			border-right: var(--size) solid transparent;
			border-bottom: var(--size) solid var(--bg-secondary-color);
			position: absolute;
			top: 2px;
			right: 8px;
			transform: rotateX(90deg);
			transform-origin: top center;
			transition:
				opacity var(--router-transition-duration) ease-out,
				transform var(--router-transition-duration) ease-out;
		}

		& > * {
			background-color: var(--bg-secondary-color);
			overflow: hidden;
		}

		&.open {
			grid-template-rows: 1fr;
			opacity: 1;
			@apply pt-3;

			&::after {
				transform: rotateX(0deg);
			}
		}
	}
}
</style>
