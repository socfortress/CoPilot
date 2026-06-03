<template>
	<div class="flex flex-wrap items-center justify-end gap-2">
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
				<div v-if="coverage" class="flex flex-col gap-2">
					<div class="box">
						Tactics:
						<code>{{ coverage.stats.total_tactics }}</code>
					</div>
					<div class="box">
						Techniques:
						<code>{{ coverage.stats.total_techniques }}</code>
					</div>
					<div class="box">
						Covered:
						<code>{{ coverage.stats.covered_techniques }}</code>
					</div>
					<div class="box">
						Rules in scope:
						<code>{{ coverage.stats.total_rules }}</code>
					</div>
				</div>
			</n-popover>

			<n-input
				v-model:value="searchQuery"
				size="small"
				placeholder="Search techniques or rule names..."
				class="max-w-120"
				clearable
			>
				<template #prefix>
					<Icon :name="SearchIcon" />
				</template>
			</n-input>

			<n-popover :show="showFilters" trigger="manual" overlap placement="top-end" class="px-0!">
				<template #trigger>
					<div class="bg-default rounded-lg">
						<n-badge :show="anyFiltersActive" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = !showFilters">
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
						<n-checkbox v-model:checked="onlyCovered" size="small">
							<span class="text-xs">Only covered</span>
						</n-checkbox>
					</div>
					<div class="flex justify-between gap-2 px-3 pt-2">
						<n-button size="small" quaternary @click="showFilters = false">Close</n-button>
						<n-button size="small" secondary @click="emit('reset-filters')">Reset</n-button>
					</div>
				</div>
			</n-popover>
		</div>

		<n-tooltip placement="bottom-end" class="max-w-120! px-2! py-1.5! text-xs!">
			<template #trigger>
				<n-button size="small" :disabled="!coverage" @click="emit('export-csv')">
					<template #icon>
						<Icon :name="ExportIcon" />
					</template>
					Export CSV
				</n-button>
			</template>
			Download a CSV of the current coverage (one row per technique and sub-technique, with rule counts and IDs).
		</n-tooltip>

		<n-tooltip placement="bottom-end" class="max-w-120! px-2! py-1.5! text-xs!">
			<template #trigger>
				<n-button size="small" :loading="refreshing" @click="emit('refresh')">
					<template #icon>
						<Icon :name="RefreshIcon" />
					</template>
					Refresh Matrix
				</n-button>
			</template>
			Force a re-fetch of the MITRE ATT&amp;CK STIX bundle from
			<code>github.com/mitre/cti</code>
			, bypassing the 24-hour cache. Use this if MITRE published a new release and you want the matrix to pick it
			up immediately.
		</n-tooltip>
	</div>
</template>

<script setup lang="ts">
import type {
	MitreCoverageResponse,
	PlatformFilter,
	RuleSeverity,
	RuleStatus
} from "@/types/copilotSearches.d"
import { NBadge, NButton, NCheckbox, NInput, NPopover, NSelect, NTooltip } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	coverage: MitreCoverageResponse | null
	refreshing: boolean
}>()

const emit = defineEmits<{
	(e: "export-csv"): void
	(e: "refresh"): void
	(e: "reset-filters"): void
}>()

const searchQuery = defineModel<string>("searchQuery", { default: "" })
const showFilters = defineModel<boolean>("showFilters", { default: false })
const selectedPlatform = defineModel<PlatformFilter | null>("selectedPlatform", { default: null })
const selectedSeverity = defineModel<RuleSeverity | null>("selectedSeverity", { default: null })
const selectedStatus = defineModel<RuleStatus | null>("selectedStatus", { default: null })
const hasGraylogFilter = defineModel<boolean>("hasGraylogFilter", { default: false })
const onlyCovered = defineModel<boolean>("onlyCovered", { default: false })

const anyFiltersActive = computed(
	() => !!selectedPlatform.value || !!selectedSeverity.value || !!selectedStatus.value || hasGraylogFilter.value
)

const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"
const FilterIcon = "carbon:filter-edit"
const ExportIcon = "carbon:download"
const RefreshIcon = "carbon:renew"

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
