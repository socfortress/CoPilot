<template>
	<div class="cases-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-2">
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
						<div class="box text-success-color">
							N/D :
							<code>{{ statusUndefinedTotal }}</code>
						</div>
					</div>
				</n-popover>

				<CaseCreationButton @submitted="getData()" :only-icon="caseCreationButtonOnlyIcon" />
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
				<template v-if="casesList.length">
					<CaseItem
						v-for="item of itemsPaginated"
						:key="item.id"
						:caseData="item"
						:highlight="highlight === item.id.toString()"
						:detailsOnMounted="highlight === item.id.toString() && !highlightedItemOpened"
						class="item-appear item-appear-bottom item-appear-005"
						@opened="highlightedItemOpened = true"
						@deleted="getData()"
						@updated="updateCase($event)"
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
				v-if="itemsPaginated.length > 3"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, watch, toRefs, provide, nextTick } from "vue"
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
import _orderBy from "lodash/orderBy"
import Icon from "@/components/common/Icon.vue"
import CaseCreationButton from "./CaseCreationButton.vue"
import { useResizeObserver } from "@vueuse/core"
import type { AlertStatus } from "@/types/incidentManagement/alerts.d"
import type { Case } from "@/types/incidentManagement/cases.d"
import type { CasesFilter } from "@/api/endpoints/incidentManagement"
import CaseItem from "./CaseItem.vue"

export interface CasesListFilter {
	type: "status" | "assignedTo" | "hostname"
	value: string | AlertStatus
}

const props = defineProps<{ highlight?: string | null; preset?: CasesListFilter; hideFilters?: boolean }>()
const { highlight, preset, hideFilters } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const showFilters = ref(false)
const casesList = ref<Case[]>([])
const availableUsers = ref<string[]>([])

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const caseCreationButtonOnlyIcon = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	const list = _orderBy(casesList.value, ["id"], ["desc"])

	return list.slice(from, to)
})

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return casesList.value.length || 0
})
const statusOpenTotal = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === "OPEN").length || 0
})
const statusInProgressTotal = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === "IN_PROGRESS").length || 0
})
const statusCloseTotal = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === "CLOSED").length || 0
})
const statusUndefinedTotal = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === null).length || 0
})

const filters = ref<Partial<CasesListFilter>>({})
const lastFilters = ref<Partial<CasesListFilter>>({})

const filtered = computed<boolean>(() => {
	return !!filters.value.type && !!filters.value.value
})

const typeOptions = [
	{ label: "Status", value: "status" },
	{ label: "Assigned To", value: "assignedTo" },
	{ label: "Hostname", value: "hostname" }
]

const statusOptions: { label: string; value: AlertStatus }[] = [
	{ label: "Open", value: "OPEN" },
	{ label: "Closed", value: "CLOSED" },
	{ label: "In progress", value: "IN_PROGRESS" }
]

const usersOptions = computed(() => availableUsers.value.map(o => ({ label: o, value: o })))

const highlightedItemFound = ref(!highlight.value)
const highlightedItemOpened = ref(!highlight.value)

watch(pageSize, () => {
	if (currentPage.value !== 1) {
		currentPage.value = 1
	}
})

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

watch(
	itemsPaginated,
	() => {
		const totalPages = Math.ceil(casesList.value.length / pageSize.value)

		if (
			itemsPaginated.value.length &&
			!itemsPaginated.value.find(o => o.id.toString() === highlight.value) &&
			currentPage.value < totalPages &&
			!highlightedItemFound.value
		) {
			nextTick(() => {
				currentPage.value++
			})
		}

		if (itemsPaginated.value.find(o => o.id.toString() === highlight.value)) {
			highlightedItemFound.value = true
		}
	},
	{ immediate: true }
)

provide("assignable-users", availableUsers)

function resetFilters() {
	filters.value.type = undefined
	showFilters.value = false
	getData()
}

function updateCase(updatedCase: Case) {
	const caseIndex = casesList.value.findIndex(o => o.id === updatedCase.id)
	if (caseIndex !== -1) {
		casesList.value[caseIndex] = updatedCase
	}
}

function getData() {
	showFilters.value = false
	loading.value = true

	lastFilters.value = _cloneDeep(filters.value)

	let query: CasesFilter | undefined = undefined
	if (filtered.value) {
		// @ts-expect-error filters properties infer are ignored
		query = { [filters.value.type]: filters.value.value }
	}

	Api.incidentManagement
		.getCasesList(query)
		.then(res => {
			if (res.data.success) {
				casesList.value = res.data?.cases || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			casesList.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
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

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550

	caseCreationButtonOnlyIcon.value = (width < 580 && width > 549) || width < 390
})

onBeforeMount(() => {
	if (preset.value?.type && preset.value.value) {
		filters.value.type = preset.value.type
		filters.value.value = preset.value.value
	}

	getData()
	getAvailableUsers()
})
</script>

<style lang="scss" scoped>
.cases-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
