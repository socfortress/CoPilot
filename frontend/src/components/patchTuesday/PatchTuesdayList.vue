<template>
	<div class="flex flex-col gap-4">
		<!-- Header -->
		<div class="flex items-center justify-between gap-4">
			<h1 class="text-2xl font-bold">Microsoft Patch Tuesday</h1>
		</div>

		<!-- Stats Cards -->
		<PatchTuesdayStats :summary :loading />

		<!-- Filters -->
		<PatchTuesdayFilters
			ref="filtersRef"
			:cycles="availableCycles"
			:families="availableFamilies"
			:loading
			@submit="applyFilters"
		/>

		<!-- Items List -->
		<n-spin :show="loading">
			<div v-if="filteredItems.length > 0" class="grid-auto-fill-350 grid gap-4">
				<PatchTuesdayCard
					v-for="item in paginatedItems"
					:key="`${item.cve}-${item.affected.product}`"
					:item
					@click="openItemDetail(item)"
				/>
			</div>

			<n-empty
				v-else-if="!loading"
				description="No vulnerabilities found for the selected filters"
				class="py-12"
			/>
		</n-spin>

		<!-- Pagination -->
		<div v-if="filteredItems.length > pageSize" class="flex justify-center">
			<n-pagination v-model:page="currentPage" :page-count="totalPages" :page-size show-quick-jumper />
		</div>

		<!-- Detail Drawer -->
		<n-drawer v-model:show="showDetail" :width="600" placement="right" class="max-w-[98vw]">
			<n-drawer-content :title="selectedItem?.cve || 'Vulnerability Details'" closable :native-scrollbar="false">
				<PatchTuesdayDetail v-if="selectedItem" :item="selectedItem" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { PatchTuesdayFilters as FiltersType, PatchTuesdayListFilter } from "./types"
import type { PatchTuesdayItem, PatchTuesdaySummary } from "@/types/patchTuesday"
import { NDrawer, NDrawerContent, NEmpty, NPagination, NSpin, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import patchTuesdayApi from "@/api/endpoints/patchTuesday"
import PatchTuesdayCard from "./PatchTuesdayCard.vue"
import PatchTuesdayDetail from "./PatchTuesdayDetail.vue"
import PatchTuesdayFilters from "./PatchTuesdayFilters.vue"
import PatchTuesdayStats from "./PatchTuesdayStats.vue"
import { patchTuesdayListToFilters } from "./utils"

const message = useMessage()

// State
const loading = ref(false)
const items = ref<PatchTuesdayItem[]>([])
const summary = ref<PatchTuesdaySummary | null>(null)
const availableCycles = ref<string[]>([])
const currentPage = ref(1)
const pageSize = 24
const showDetail = ref(false)
const selectedItem = ref<PatchTuesdayItem | null>(null)

const filtersRef = ref<{ setFilter: (payload: PatchTuesdayListFilter[]) => void } | null>(null)
const filters = ref<FiltersType>({
	cycle: null,
	priority: null,
	family: null,
	severity: null,
	searchQuery: null,
	kevOnly: false
})

// Computed
const availableFamilies = computed(() => {
	if (!summary.value?.by_family) return []
	return Object.keys(summary.value.by_family).sort()
})

const filteredItems = computed(() => {
	let result = [...items.value]

	// Filter by priority
	if (filters.value.priority) {
		result = result.filter(item => item.prioritization.priority === filters.value.priority)
	}

	// Filter by family
	if (filters.value.family) {
		result = result.filter(item => item.affected.family === filters.value.family)
	}

	// Filter by severity
	if (filters.value.severity) {
		result = result.filter(item => item.severity?.toLowerCase() === filters.value.severity?.toLowerCase())
	}

	// Filter KEV only
	if (filters.value.kevOnly) {
		result = result.filter(item => item.kev.in_kev)
	}

	// Search filter
	if (filters.value.searchQuery) {
		const query = filters.value.searchQuery.toLowerCase()
		result = result.filter(
			item =>
				item.cve.toLowerCase().includes(query) ||
				item.title?.toLowerCase().includes(query) ||
				item.affected.product.toLowerCase().includes(query)
		)
	}

	return result
})

const totalPages = computed(() => Math.ceil(filteredItems.value.length / pageSize))

const paginatedItems = computed(() => {
	const start = (currentPage.value - 1) * pageSize
	return filteredItems.value.slice(start, start + pageSize)
})

// Methods
async function fetchCycles() {
	try {
		const response = await patchTuesdayApi.getCycles()
		if (response.data.success) {
			availableCycles.value = response.data.cycles
			if (!filters.value.cycle) {
				filters.value.cycle = response.data.current_cycle
			}
		} else {
			availableCycles.value = response.data.cycles
			if (!filters.value.cycle) {
				filters.value.cycle = response.data.current_cycle
			}
		}
	} catch (error) {
		console.error("Failed to fetch cycles:", error)
		availableCycles.value = []
		if (!filters.value.cycle) {
			filters.value.cycle = ""
		}
	}
}

async function fetchData() {
	if (!filters.value.cycle) return

	loading.value = true
	try {
		const response = await patchTuesdayApi.getPatchTuesday({
			cycle: filters.value.cycle,
			include_epss: true,
			include_kev: true
		})

		if (response.data.success) {
			items.value = response.data.items
			summary.value = response.data.summary
		} else {
			message.error(response.data.message || "Failed to fetch Patch Tuesday data")
		}
	} catch (error: unknown) {
		const errorMessage = error instanceof Error ? error.message : "Unknown error occurred"
		message.error(`Error fetching data: ${errorMessage}`)
	} finally {
		loading.value = false
	}
}

function applyFilters(newFilters: PatchTuesdayListFilter[]) {
	const prevCycle = filters.value.cycle
	filters.value = patchTuesdayListToFilters(newFilters)
	currentPage.value = 1
	if (filters.value.cycle && filters.value.cycle !== prevCycle) {
		fetchData()
	}
}

function openItemDetail(item: PatchTuesdayItem) {
	selectedItem.value = item
	showDetail.value = true
}

// Lifecycle
onMounted(async () => {
	await fetchCycles()
	if (filters.value.cycle) {
		filtersRef.value?.setFilter([{ type: "cycle", value: filters.value.cycle }])
		await fetchData()
	}
})
</script>
