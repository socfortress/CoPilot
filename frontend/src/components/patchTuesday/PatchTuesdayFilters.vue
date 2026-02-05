<template>
	<n-card size="small" :bordered="false" class="filters-card">
		<div class="filters-container">
			<!-- Cycle Selector -->
			<div class="filter-item">
				<label class="filter-label">Cycle</label>
				<n-select
					:value="filters.cycle"
					:options="cycleOptions"
					:loading="loading"
					placeholder="Select cycle"
					style="min-width: 140px"
					@update:value="updateFilter('cycle', $event)"
				/>
			</div>

			<!-- Priority Filter -->
			<div class="filter-item">
				<label class="filter-label">Priority</label>
				<n-select
					:value="filters.priority"
					:options="priorityOptions"
					clearable
					placeholder="All priorities"
					style="min-width: 140px"
					@update:value="updateFilter('priority', $event)"
				/>
			</div>

			<!-- Family Filter -->
			<div class="filter-item">
				<label class="filter-label">Product Family</label>
				<n-select
					:value="filters.family"
					:options="familyOptions"
					clearable
					placeholder="All families"
					style="min-width: 160px"
					@update:value="updateFilter('family', $event)"
				/>
			</div>

			<!-- Severity Filter -->
			<div class="filter-item">
				<label class="filter-label">Severity</label>
				<n-select
					:value="filters.severity"
					:options="severityOptions"
					clearable
					placeholder="All severities"
					style="min-width: 140px"
					@update:value="updateFilter('severity', $event)"
				/>
			</div>

			<!-- Search -->
			<div class="filter-item search-item">
				<label class="filter-label">Search</label>
				<n-input
					:value="filters.searchQuery"
					placeholder="CVE, title, or product..."
					clearable
					style="min-width: 200px"
					@update:value="updateFilter('searchQuery', $event)"
				>
					<template #prefix>
						<Icon :name="SearchIcon" />
					</template>
				</n-input>
			</div>

			<!-- KEV Only Toggle -->
			<div class="filter-item toggle-item">
				<n-tooltip trigger="hover">
					<template #trigger>
						<n-switch
							:value="filters.kevOnly"
							@update:value="updateFilter('kevOnly', $event)"
						>
							<template #checked>KEV</template>
							<template #unchecked>KEV</template>
						</n-switch>
					</template>
					Show only Known Exploited Vulnerabilities
				</n-tooltip>
			</div>

			<!-- Clear Filters -->
			<div class="filter-item">
				<n-button quaternary size="small" @click="clearFilters">
					<template #icon>
						<Icon :name="ClearIcon" />
					</template>
					Clear
				</n-button>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { PatchTuesdayFilters } from "./types"
import { NButton, NCard, NInput, NSelect, NSwitch, NTooltip } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { PriorityLevel } from "@/types/patchTuesday.d"

const props = defineProps<{
    filters: PatchTuesdayFilters
    cycles: string[]
    families: string[]
    loading?: boolean
}>()
const emit = defineEmits<{
    (e: "update:filters", filters: PatchTuesdayFilters): void
}>()
const SearchIcon = "carbon:search"
const ClearIcon = "carbon:close"

const cycleOptions = computed(() =>
    props.cycles.map(cycle => ({
        label: cycle,
        value: cycle
    }))
)

const priorityOptions = [
    { label: "P0 - Emergency", value: PriorityLevel.P0 },
    { label: "P1 - High", value: PriorityLevel.P1 },
    { label: "P2 - Medium", value: PriorityLevel.P2 },
    { label: "P3 - Low", value: PriorityLevel.P3 }
]

const familyOptions = computed(() =>
    props.families.map(family => ({
        label: family,
        value: family
    }))
)

const severityOptions = [
    { label: "Critical", value: "critical" },
    { label: "Important", value: "important" },
    { label: "Moderate", value: "moderate" },
    { label: "Low", value: "low" }
]

function updateFilter<K extends keyof PatchTuesdayFilters>(key: K, value: PatchTuesdayFilters[K]) {
    emit("update:filters", {
        ...props.filters,
        [key]: value
    })
}

function clearFilters() {
    emit("update:filters", {
        cycle: props.filters.cycle, // Keep cycle selected
        priority: null,
        family: null,
        severity: null,
        searchQuery: "",
        kevOnly: false
    })
}
</script>

<style scoped lang="scss">
.filters-card {
    background: var(--bg-secondary-color);
    border-radius: 8px;

    .filters-container {
        display: flex;
        flex-wrap: wrap;
        align-items: flex-end;
        gap: 16px;
    }

    .filter-item {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .filter-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.7;
        }

        &.search-item {
            flex: 1;
            min-width: 200px;
        }

        &.toggle-item {
            padding-bottom: 4px;
        }
    }
}
</style>
