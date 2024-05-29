<template>
	<div class="soc-cases-list">
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

				<n-button
					size="small"
					type="error"
					ghost
					@click="handlePurge()"
					:loading="loadingPurge"
					v-if="casesList.length"
				>
					<div class="flex items-center gap-2">
						<Icon :name="TrashIcon" :size="16"></Icon>
						<span class="hidden xs:block">Purge</span>
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
					<div class="px-3 flex justify-end gap-2">
						<n-button size="small" @click="showFilters = false" secondary>Close</n-button>
						<n-button size="small" @click="getData()" type="primary" secondary>Submit</n-button>
					</div>
				</div>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="list my-3">
				<template v-if="casesList.length">
					<SocCaseItem
						v-for="caseData of itemsPaginated"
						:key="caseData.case_id"
						:caseData="caseData"
						@deleted="getData()"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
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
	NInputNumber,
	useDialog
} from "naive-ui"
import Api from "@/api"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import type { CasesFilter } from "@/api/soc"
import type { DateFormatted, SocCase } from "@/types/soc/case.d"
import SocCaseItem from "./SocCaseItem.vue"
import dayjs from "@/utils/dayjs"

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

<style lang="scss" scoped>
.soc-cases-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
