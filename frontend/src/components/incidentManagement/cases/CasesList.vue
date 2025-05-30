<template>
	<div class="cases-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
				<n-popover overlap placement="left">
					<template #trigger>
						<div class="bg-default rounded-lg">
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
						<div class="box text-error">
							Open :
							<code>{{ statusOpenTotal }}</code>
						</div>
						<div class="box text-warning">
							In Progress :
							<code>{{ statusInProgressTotal }}</code>
						</div>
						<div class="box text-success">
							Close :
							<code>{{ statusCloseTotal }}</code>
						</div>
						<div class="box text-secondary">
							N/D :
							<code>{{ statusUndefinedTotal }}</code>
						</div>
					</div>
				</n-popover>

				<n-popover v-if="showMobileMenu" overlap placement="left" display-directive="show">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="!cursor-pointer">
								<template #icon>
									<Icon :name="MenuIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2 py-1">
						<CasesExport show-icon size="small" />
						<CaseCreationButton show-icon size="small" @submitted="getData()" />
					</div>
				</n-popover>

				<CasesExport v-if="!showMobileMenu" :show-icon="caseExportButtonShowIcon" size="small" />

				<CaseCreationButton
					v-if="!showMobileMenu"
					:show-icon="caseCreationButtonShowIcon"
					size="small"
					@submitted="getData()"
				/>
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
			<n-popover v-if="!hideFilters" :show="showFilters" trigger="manual" overlap placement="right" class="!px-0">
				<template #trigger>
					<div class="bg-default rounded-lg">
						<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon"></Icon>
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<div class="flex flex-col gap-2 py-1">
					<div class="px-3">
						<n-input-group>
							<n-select
								v-model:value="filters.type"
								:options="typeOptions"
								placeholder="Filter by..."
								clearable
								class="!w-40"
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
								filterable
								class="!w-56"
							/>
							<n-select
								v-else-if="filters.type === 'customerCode'"
								v-model:value="filters.value"
								:options="customersOptions"
								placeholder="Value..."
								:disabled="!filters.type"
								clearable
								filterable
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
					<div class="flex justify-between gap-2 px-3">
						<div class="flex justify-start gap-2">
							<n-button size="small" quaternary @click="showFilters = false">Close</n-button>
						</div>
						<div class="flex justify-end gap-2">
							<n-button size="small" secondary @click="resetFilters()">Reset</n-button>
							<n-button size="small" type="primary" secondary :loading @click="getData()">
								Submit
							</n-button>
						</div>
					</div>
				</div>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="casesList.length">
					<CaseItem
						v-for="item of itemsPaginated"
						:key="item.id"
						:case-data="item"
						:highlight="highlight === item.id.toString()"
						:details-on-mounted="highlight === item.id.toString() && !highlightedItemOpened"
						class="item-appear item-appear-bottom item-appear-005"
						@opened="highlightedItemOpened = true"
						@deleted="getData()"
						@updated="updateCase($event)"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-if="itemsPaginated.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CasesFilter, CasesFilterTypes } from "@/api/endpoints/incidentManagement/cases"
import type { Customer } from "@/types/customers.d"
import type { Case, CaseStatus } from "@/types/incidentManagement/cases.d"
import { useResizeObserver } from "@vueuse/core"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import {
	NBadge,
	NButton,
	NEmpty,
	NInput,
	NInputGroup,
	NPagination,
	NPopover,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, nextTick, onBeforeMount, provide, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CaseCreationButton from "./CaseCreationButton.vue"
import CaseItem from "./CaseItem.vue"
import CasesExport from "./CasesExport.vue"

export interface CasesListFilter {
	type: CasesFilterTypes
	value: string | CaseStatus
}

const props = defineProps<{ highlight?: string | null; preset?: CasesListFilter; hideFilters?: boolean }>()
const { highlight, preset, hideFilters } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const showFilters = ref(false)
const casesList = ref<Case[]>([])
const availableUsers = ref<string[]>([])
const customersList = ref<Customer[]>([])

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const caseCreationButtonShowIcon = ref(false)
const caseExportButtonShowIcon = ref(false)
const showMobileMenu = ref(false)
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
const MenuIcon = "carbon:overflow-menu-horizontal"
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

const typeOptions: { label: string; value: CasesFilterTypes }[] = [
	{ label: "Status", value: "status" },
	{ label: "Assigned To", value: "assignedTo" },
	{ label: "Hostname", value: "hostname" },
	{ label: "Customer Code", value: "customerCode" }
]

const statusOptions: { label: string; value: CaseStatus }[] = [
	{ label: "Open", value: "OPEN" },
	{ label: "Closed", value: "CLOSED" },
	{ label: "In progress", value: "IN_PROGRESS" }
]

const usersOptions = computed(() => availableUsers.value.map(o => ({ label: o, value: o })))
const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

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
provide("customers-list", customersList)

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

	let query: CasesFilter | undefined
	if (filtered.value) {
		// @ts-expect-error filters properties infer are ignored
		query = { [filters.value.type]: filters.value.value }
	}

	Api.incidentManagement.cases
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
	Api.incidentManagement.alerts
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

function getCustomers() {
	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
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
	caseCreationButtonShowIcon.value = width >= 580
	caseExportButtonShowIcon.value = width >= 580
	showMobileMenu.value = width <= 420
})

onBeforeMount(() => {
	if (preset.value?.type && preset.value.value) {
		filters.value.type = preset.value.type
		filters.value.value = preset.value.value
	}

	getData()
	getAvailableUsers()
	getCustomers()
})
</script>
