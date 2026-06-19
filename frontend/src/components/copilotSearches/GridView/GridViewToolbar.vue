<template>
	<div class="flex flex-wrap items-center justify-between gap-2">
		<div class="flex min-w-80 grow gap-2">
			<n-popover overlap placement="bottom-start">
				<template #trigger>
					<div class="bg-default rounded-lg">
						<n-button size="small" class="cursor-help!">
							<template #icon>
								<Icon :name="InfoIcon" />
							</template>
						</n-button>
					</div>
				</template>
				<div class="flex flex-col gap-2">
					<div class="box">
						Total Rules:
						<code>{{ pagination.total }}</code>
					</div>
					<div class="box">
						Filtered:
						<code>{{ pagination.filtered }}</code>
					</div>
				</div>
			</n-popover>

			<n-input v-model:value="searchQuery" size="small" placeholder="Search rules..." class="max-w-120" clearable>
				<template #prefix>
					<Icon :name="SearchIcon" />
				</template>
			</n-input>

			<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="px-0!">
				<template #trigger>
					<div class="bg-default rounded-lg">
						<n-badge :show="hasActiveFilters" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon" />
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<div class="divide-border flex w-50 flex-col gap-0 divide-y">
					<div class="flex flex-col gap-2.5 px-3 pt-1 pb-3">
						<n-select
							v-model:value="selectedPlatform"
							:options="platformOptions"
							size="small"
							placeholder="Platform"
							class="w-full"
							clearable
							:consistent-menu-width="false"
						/>

						<n-select
							v-model:value="selectedSeverity"
							:options="severityOptions"
							clearable
							size="small"
							placeholder="Severity"
							class="w-full"
							:consistent-menu-width="false"
						/>

						<n-select
							v-model:value="selectedStatus"
							:options="statusOptions"
							clearable
							size="small"
							placeholder="Status"
							class="w-full"
							:consistent-menu-width="false"
						/>

						<n-checkbox v-model:checked="hasGraylogFilter" size="small">
							<span class="text-xs">Graylog Only</span>
						</n-checkbox>
					</div>
					<div class="flex justify-between gap-2 px-3 pt-2">
						<div class="flex justify-start gap-2">
							<n-button size="small" quaternary @click="showFilters = false">Close</n-button>
						</div>
						<div class="flex justify-end gap-2">
							<n-button size="small" secondary @click="emit('reset-filters')">Reset</n-button>
						</div>
					</div>
				</div>
			</n-popover>
		</div>

		<div v-if="!hideSelectionSwitch">
			<n-button
				size="small"
				secondary
				:type="selectMode ? 'primary' : 'default'"
				@click="emit('toggle-select-mode')"
			>
				<template #icon>
					<Icon :name="SelectIcon" />
				</template>
				{{ selectMode ? "Exit select" : "Select" }}
			</n-button>
		</div>

		<n-button size="small" :loading="refreshing" @click="emit('refresh')">
			<template #icon>
				<Icon :name="RefreshIcon" />
			</template>
			Refresh Cache
		</n-button>

		<slot />
	</div>
</template>

<script setup lang="ts">
import type { PlatformFilter, RuleSeverity, RuleStatus } from "@/types/copilotSearches"
import { NBadge, NButton, NCheckbox, NInput, NPopover, NSelect } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	pagination: { total: number; filtered: number }
	selectMode: boolean
	hideSelectionSwitch: boolean
	refreshing: boolean
}>()

const emit = defineEmits<{
	(e: "refresh"): void
	(e: "toggle-select-mode"): void
	(e: "reset-filters"): void
}>()

const searchQuery = defineModel<string | null>("searchQuery", { default: null })
const showFilters = defineModel<boolean>("showFilters", { default: false })
const selectedPlatform = defineModel<PlatformFilter | null>("selectedPlatform", { default: null })
const selectedSeverity = defineModel<RuleSeverity | null>("selectedSeverity", { default: null })
const selectedStatus = defineModel<RuleStatus | null>("selectedStatus", { default: null })
const hasGraylogFilter = defineModel<boolean>("hasGraylogFilter", { default: false })

const hasActiveFilters = computed(
	() => !!selectedPlatform.value || !!selectedSeverity.value || !!selectedStatus.value || hasGraylogFilter.value
)

const InfoIcon = "carbon:information"
const FilterIcon = "carbon:filter-edit"
const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:renew"
const SelectIcon = "carbon:checkbox-checked"

const platformOptions = [
	{ label: "Linux", value: "linux" },
	{ label: "Windows", value: "windows" },
	{ label: "PowerShell", value: "powershell" },
	{ label: "CVE", value: "cve" }
]

const severityOptions = [
	{ label: "Low", value: "low" },
	{ label: "Medium", value: "medium" },
	{ label: "High", value: "high" },
	{ label: "Critical", value: "critical" }
]

const statusOptions = [
	{ label: "Production", value: "production" },
	{ label: "Experimental", value: "experimental" },
	{ label: "Deprecated", value: "deprecated" }
]
</script>
