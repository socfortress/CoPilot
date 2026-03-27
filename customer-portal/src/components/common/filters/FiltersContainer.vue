<template>
	<div class="flex flex-col gap-0.5">
		<CollapseKeepAlive :show="showFilters">
			<n-scrollbar x-scrollable class="rounded-lg" trigger="none" content-class="max-h-full overflow-y-hidden!">
				<div class="mb-3 flex max-h-60 items-stretch gap-2 overflow-hidden">
					<slot />
				</div>
			</n-scrollbar>
		</CollapseKeepAlive>

		<div class="flex items-start justify-between gap-2">
			<div class="flex flex-wrap gap-2">
				<slot name="filters-toolbar-prefix" />
				<Chip size="small" clickable @click="collapseFilters">
					<div class="flex items-center gap-1">
						<span>Filters</span>
						<Icon
							name="carbon:chevron-down"
							:size="16"
							:class="{ '-rotate-90': !showFilters }"
							class="transition-transform duration-200"
						/>
					</div>
				</Chip>
				<slot name="filters-toolbar-after-collapse-button" />
				<div v-for="filter in activeFiltersSummary" :key="filter.id" class="flex items-center gap-1">
					<Chip size="small" closable @close="clearFilter(filter.id)">
						<span class="text-secondary uppercase">{{ filter.label }}</span>
						<span>{{ filter.displayValue }}</span>
					</Chip>
				</div>

				<Chip v-if="activeFiltersSummary.length > 1" size="small" clickable @click="clearAllFilters()">
					<span>Reset filters</span>
				</Chip>
			</div>

			<slot name="filters-toolbar-side" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { FilterInfo, FilterValue } from "./types"
import { NScrollbar } from "naive-ui"
import { computed, onBeforeUnmount, provide, ref } from "vue"
import Chip from "@/components/common/Chip.vue"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"

const filters = ref<Map<string, FilterInfo>>(new Map())
const showFilters = ref(true)

function registerFilter(id: string, info: Omit<FilterInfo, "id">) {
	filters.value.set(id, { id, ...info })
}

function unregisterFilter(id: string) {
	filters.value.delete(id)
}

function updateFilter(id: string, value: FilterValue) {
	const filter = filters.value.get(id)
	if (filter) {
		filter.value = value
	}
}

function getFilterDisplayValue(filter: FilterInfo): string {
	if (filter.value === undefined || (Array.isArray(filter.value) && filter.value.length === 0)) {
		return ""
	}

	if (Array.isArray(filter.value)) {
		if (filter.options) {
			const selectedLabels = filter.value.map(val => {
				const option = filter.options?.find(opt => `${opt.value}` === `${val}`)
				return option ? option.label : String(val)
			})
			return selectedLabels.length > 0 ? selectedLabels.join(" // ") : filter.value.join(" // ")
		}
		return filter.value.join(", ")
	}

	if (filter.options) {
		const option = filter.options.find(opt => opt.value === filter.value)
		return option ? option.label : String(filter.value)
	}

	return String(filter.value)
}

const activeFiltersSummary = computed(() => {
	return [...filters.value.values()]
		.filter(filter => {
			if (filter.value === undefined) return false
			if (Array.isArray(filter.value)) {
				return filter.value.length > 0
			}
			return filter.value !== null && filter.value !== ""
		})
		.map(filter => ({
			id: filter.id,
			label: filter.label,
			displayValue: getFilterDisplayValue(filter),
			clearFilter: filter.clearFilter
		}))
})

function clearFilter(id: string) {
	const filter = filters.value.get(id)
	if (filter) {
		filter.clearFilter()
	}
}

function clearAllFilters() {
	for (const filter of filters.value.values()) {
		filter.clearFilter()
	}
}

function collapseFilters() {
	showFilters.value = !showFilters.value
}

provide("filtersContainer", {
	registerFilter,
	unregisterFilter,
	updateFilter
})

onBeforeUnmount(() => {
	filters.value.clear()
})
</script>
