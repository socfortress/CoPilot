<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info">
			SCA Overview provides real-time Security Configuration Assessment results from Wazuh Manager across all
			agents with comprehensive compliance scoring.
		</n-alert>

		<ScaStats
			:filters
			class="my-8"
			@update:min_score="selectMinScore"
			@update:max_score="selectMaxScore"
			@update:policy_id="selectPolicyID"
		/>

		<div ref="header" class="flex items-center justify-end gap-2">
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot
				:page-sizes
				:item-count="totalCount"
				:show-size-picker
			/>
			<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
				<n-button size="small" secondary @click="showFiltersView = !showFiltersView">
					<template #icon>
						<Icon :name="FilterIcon" />
					</template>
				</n-button>
			</n-badge>
		</div>

		<CollapseKeepAlive :show="showFiltersView" embedded arrow="top-right">
			<ListFilters class="p-3" @submit="applyFilters" @mounted="filtersCTX = $event" />
		</CollapseKeepAlive>

		<!-- SCA Results List -->
		<n-spin :show="loading">
			<div class="my-3">
				<div v-if="list.length" class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					<ScaCard v-for="item of list" :key="JSON.stringify(item)" :sca="item" />
				</div>
				<template v-else>
					<n-empty v-if="!loading" description="No SCA results found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>

		<div v-if="list.length >= 9" class="flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot
				:page-sizes
				:item-count="totalCount"
				:show-size-picker
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ScaOverviewFilter, ScaOverviewFilterTypes } from "./types"
import type { AgentScaOverviewItem, ScaOverviewQuery } from "@/types/sca.d"
import { useResizeObserver, useStorage, watchDebounced } from "@vueuse/core"
import axios from "axios"
import _set from "lodash/set"
import _toNumber from "lodash/toSafeInteger"
import { NAlert, NBadge, NButton, NEmpty, NPagination, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"
import ListFilters from "./ListFilters.vue"
import ScaCard from "./ScaCard.vue"
import ScaStats from "./ScaStats.vue"

const loading = ref(false)
const message = useMessage()
const list = ref<AgentScaOverviewItem[]>([])
const pageSizes = [10, 25, 50, 100]
const pageSize = ref(pageSizes[1])
const pageSlot = ref(8)
const showSizePicker = ref(true)
const header = ref()
const showFiltersView = useStorage<boolean>("agents-sca-list-filters-view-state", false, localStorage)

const filtersCTX = ref<{ setFilter: (payload: ScaOverviewFilter[]) => void } | null>(null)
const filters = ref<ScaOverviewFilter[]>([])

const filtered = computed<boolean>(() => {
	return !!filters.value.length
})

const totalCount = ref(0)
const currentPage = ref(1)

const FilterIcon = "carbon:filter-edit"

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: ScaOverviewQuery = {
		page: currentPage.value,
		page_size: pageSize.value
	}

	for (const key of ["customer_code", "policy_id", "policy_name", "agent_name"] as ScaOverviewFilterTypes[]) {
		if (filters.value.find(o => o.type === key)?.value) {
			_set(query, key, `${filters.value.find(o => o.type === key)?.value}`)
		}
	}
	for (const key of ["min_score", "max_score"] as ScaOverviewFilterTypes[]) {
		if (filters.value.find(o => o.type === key)?.value) {
			_set(query, key, _toNumber(filters.value.find(o => o.type === key)?.value))
		}
	}

	Api.sca
		.searchScaOverview(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.sca_results || []
				totalCount.value = res.data?.total_count || 0
				currentPage.value = res.data?.page || 1
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loading.value = false
			}
		})
}

function selectPolicyID(value: string) {
	showFiltersView.value = true
	filtersCTX.value?.setFilter([{ type: "policy_id", value }])
}

function selectMinScore(value: number) {
	showFiltersView.value = true
	filtersCTX.value?.setFilter([{ type: "min_score", value }])
}

function selectMaxScore(value: number) {
	showFiltersView.value = true
	filtersCTX.value?.setFilter([{ type: "max_score", value }])
}

function applyFilters(newFilters: ScaOverviewFilter[]) {
	filters.value = newFilters
}

watchDebounced(
	currentPage,
	() => {
		getList()
	},
	{ debounce: 300 }
)

watchDebounced(
	pageSize,
	() => {
		currentPage.value = 1
		getList()
	},
	{ debounce: 300 }
)

watchDebounced(
	filters,
	() => {
		currentPage.value = 1
		getList()
	},
	{ deep: true, debounce: 300, immediate: true }
)

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	showSizePicker.value = width > 550
})
</script>
