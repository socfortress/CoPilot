<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info">
			Vulnerability Overview provides real-time vulnerability data from Wazuh Indexer with EPSS scoring and
			detailed package information.
		</n-alert>

		<VulnerabilityStats :filters class="my-8" @update:severity="selectSeverity" @update:package="selectPackage" />

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
						<Icon :name="FilterIcon"></Icon>
					</template>
				</n-button>
			</n-badge>
		</div>

		<CollapseKeepAlive :show="showFiltersView" embedded arrow="top-right">
			<ListFilters class="p-3" @submit="applyFilters" @mounted="filtersCTX = $event" />
		</CollapseKeepAlive>

		<!-- Vulnerability List -->
		<n-spin :show="loading">
			<div class="my-3">
				<div v-if="list.length" class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					<VulnerabilityCard v-for="item of list" :key="JSON.stringify(item)" :vulnerability="item" />
				</div>
				<template v-else>
					<n-empty v-if="!loading" description="No vulnerabilities found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>

		<div class="flex justify-end">
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
import type { VulnerabilitiesListFilter } from "./types"
import type {
	VulnerabilitySearchItem,
	VulnerabilitySearchQuery,
	VulnerabilitySeverity
} from "@/types/vulnerabilities.d"
import { useResizeObserver, useStorage, watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NAlert, NBadge, NButton, NEmpty, NPagination, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"
import ListFilters from "./ListFilters.vue"
import VulnerabilityCard from "./VulnerabilityCard.vue"
import VulnerabilityStats from "./VulnerabilityStats.vue"

const loading = ref(false)
const message = useMessage()
const list = ref<VulnerabilitySearchItem[]>([])
const pageSizes = [10, 25, 50, 100]
const pageSize = ref(pageSizes[1])
const pageSlot = ref(8)
const showSizePicker = ref(true)
const header = ref()
const showFiltersView = useStorage<boolean>("agents-vulnerability-list-filters-view-state", false, localStorage)

const filtersCTX = ref<{ setFilter: (payload: VulnerabilitiesListFilter[]) => void } | null>(null)
const filters = ref<VulnerabilitiesListFilter[]>([])

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

	const query: VulnerabilitySearchQuery = {
		page: currentPage.value,
		page_size: pageSize.value,
		customer_code: filters.value.find(o => o.type === "customer_code")?.value || undefined,
		severity: (filters.value.find(o => o.type === "severity")?.value as VulnerabilitySeverity) || undefined,
		cve_id: filters.value.find(o => o.type === "cve_id")?.value || undefined,
		agent_name: filters.value.find(o => o.type === "agent_name")?.value || undefined,
		package_name: filters.value.find(o => o.type === "package_name")?.value || undefined,
		include_epss: true
	}

	Api.vulnerabilities
		.searchVulnerabilities(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.vulnerabilities || []
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

function selectSeverity(value: VulnerabilitySeverity) {
	filtersCTX.value?.setFilter([{ type: "severity", value }])
}

function selectPackage(value: string) {
	filtersCTX.value?.setFilter([{ type: "package_name", value }])
}

function applyFilters(newFilters: VulnerabilitiesListFilter[]) {
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
