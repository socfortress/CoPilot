<template>
	<div class="soc-cases-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
				<n-popover overlap placement="bottom-start">
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
					</div>
				</n-popover>

				<n-button
					v-if="casesList.length"
					size="small"
					type="error"
					ghost
					:loading="loadingPurge"
					@click="handlePurge()"
				>
					<div class="flex items-center gap-2">
						<Icon :name="TrashIcon" :size="16"></Icon>
						<span class="xs:block hidden">Purge</span>
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
			<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="!px-0">
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
						<small>Cases older then:</small>
					</div>
					<div class="px-3">
						<n-input-group>
							<n-select
								v-model:value="filters.unit"
								:options="unitOptions"
								placeholder="Time unit"
								clearable
								class="!w-28"
							/>
							<n-input-number
								v-model:value="filters.olderThan"
								clearable
								placeholder="Time"
								class="!w-32"
							/>
						</n-input-group>
					</div>
					<div class="flex justify-end gap-2 px-3">
						<n-button size="small" secondary @click="showFilters = false">Close</n-button>
						<n-button size="small" type="primary" secondary @click="getData()">Submit</n-button>
					</div>
				</div>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="casesList.length">
					<SocCaseItem
						v-for="caseData of itemsPaginated"
						:key="caseData.case_id"
						:case-data="caseData"
						class="item-appear item-appear-bottom item-appear-005"
						@deleted="getData()"
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
import type { CasesFilter } from "@/api/endpoints/soc"
import type { DateFormatted, SocCase } from "@/types/soc/case.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"
import { useResizeObserver } from "@vueuse/core"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import {
	NBadge,
	NButton,
	NEmpty,
	NInputGroup,
	NInputNumber,
	NPagination,
	NPopover,
	NSelect,
	NSpin,
	useDialog,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import SocCaseItem from "./SocCaseItem.vue"

const dialog = useDialog()
const message = useMessage()
const loadingPurge = ref(false)
const loading = ref(false)
const showFilters = ref(false)
const casesList = ref<SocCase[]>([])

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

	const list = _orderBy(
		casesList.value.map(o => {
			o.case_open_date = dayjs(o.case_open_date).format("YYYY/MM/DD") as DateFormatted
			return o
		}),
		["case_open_date"],
		["desc"]
	)

	return list.slice(from, to)
})

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"
const TrashIcon = "carbon:trash-can"

const total = computed<number>(() => {
	return casesList.value.length || 0
})

const filters = ref<Partial<CasesFilter>>({})
const lastFilters = ref<Partial<CasesFilter>>({})

const filtered = computed<boolean>(() => {
	return !!filters.value.unit && !!filters.value.olderThan
})

const unitOptions = [
	{ label: "Hours", value: "hours" },
	{ label: "Days", value: "days" },
	{ label: "Weeks", value: "weeks" }
]

watch(showFilters, val => {
	if (!val) {
		filters.value = _cloneDeep(lastFilters.value)
	}
})

function getData() {
	showFilters.value = false
	loading.value = true

	lastFilters.value = _cloneDeep(filters.value)

	Api.soc
		.getCases(filtered?.value ? (lastFilters.value as CasesFilter) : undefined)
		.then(res => {
			if (res.data.success) {
				casesList.value = res.data?.cases || res.data?.cases_breached || []
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

function handlePurge() {
	dialog.warning({
		title: "Confirm",
		content: "This will remove ALL cases, are you sure you want to proceed?",
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			purge()
		},
		onNegativeClick: () => {
			message.info("Purge canceled")
		}
	})
}

function purge() {
	loadingPurge.value = true

	Api.soc
		.purgeAllCases()
		.then(res => {
			if (res.data.success) {
				getData()
				message.success(res.data?.message || "SOC Cases purged successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingPurge.value = false
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
