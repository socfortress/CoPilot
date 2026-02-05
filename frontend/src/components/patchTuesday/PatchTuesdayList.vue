<template>
    <div class="patch-tuesday-list">
        <!-- Header -->
        <div class="header flex items-center justify-between gap-4 mb-4">
            <div class="flex items-center gap-3">
                <Icon :name="CalendarIcon" :size="26" class="text-primary-color" />
                <h1 class="text-2xl font-bold">Microsoft Patch Tuesday</h1>
            </div>
            <div class="flex items-center gap-2">
                <n-button
                    :loading="loading"
                    :disabled="loading"
                    type="primary"
                    secondary
                    @click="fetchData"
                >
                    <template #icon>
                        <Icon :name="RefreshIcon" />
                    </template>
                    Refresh
                </n-button>
            </div>
        </div>

        <!-- Stats Cards -->
        <PatchTuesdayStats :summary="summary" :loading="loading" class="mb-4" />

        <!-- Filters -->
        <PatchTuesdayFilters
            v-model:filters="filters"
            :cycles="availableCycles"
            :families="availableFamilies"
            :loading="loading"
            class="mb-4"
            @update:filters="handleFiltersChange"
        />

        <!-- Items List -->
        <n-spin :show="loading">
            <div v-if="filteredItems.length > 0" class="items-grid">
                <PatchTuesdayCard
                    v-for="item in paginatedItems"
                    :key="`${item.cve}-${item.affected.product}`"
                    :item="item"
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
        <div v-if="filteredItems.length > pageSize" class="flex justify-center mt-4">
            <n-pagination
                v-model:page="currentPage"
                :page-count="totalPages"
                :page-size="pageSize"
                show-quick-jumper
            />
        </div>

        <!-- Detail Drawer -->
        <n-drawer v-model:show="showDetail" :width="600" placement="right">
            <n-drawer-content :title="selectedItem?.cve || 'Vulnerability Details'" closable>
                <PatchTuesdayDetail v-if="selectedItem" :item="selectedItem" />
            </n-drawer-content>
        </n-drawer>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import { NButton, NDrawer, NDrawerContent, NEmpty, NPagination, NSpin, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import patchTuesdayApi from "@/api/endpoints/patchTuesday"
import type { PatchTuesdayItem, PatchTuesdaySummary } from "@/types/patchTuesday.d"
import type { PatchTuesdayFilters as FiltersType } from "./types"
import PatchTuesdayStats from "./PatchTuesdayStats.vue"
import PatchTuesdayFilters from "./PatchTuesdayFilters.vue"
import PatchTuesdayCard from "./PatchTuesdayCard.vue"
import PatchTuesdayDetail from "./PatchTuesdayDetail.vue"

const CalendarIcon = "carbon:calendar"
const RefreshIcon = "carbon:refresh"

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

const filters = ref<FiltersType>({
    cycle: "",
    priority: null,
    family: null,
    severity: null,
    searchQuery: "",
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
            if (!filters.value.cycle && response.data.current_cycle) {
                filters.value.cycle = response.data.current_cycle
            }
        }
    } catch (error) {
        console.error("Failed to fetch cycles:", error)
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

function handleFiltersChange() {
    currentPage.value = 1
    if (filters.value.cycle) {
        fetchData()
    }
}

function openItemDetail(item: PatchTuesdayItem) {
    selectedItem.value = item
    showDetail.value = true
}

// Watch for cycle changes
watch(
    () => filters.value.cycle,
    newCycle => {
        if (newCycle) {
            fetchData()
        }
    }
)

// Lifecycle
onMounted(async () => {
    await fetchCycles()
})
</script>

<style scoped lang="scss">
.patch-tuesday-list {
    .items-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
        gap: 16px;
    }
}
</style>
