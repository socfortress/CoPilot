<template>
	<div class="flex flex-wrap gap-3">
		<div v-for="filter of filters" :key="filter.type">
			<n-input-group v-if="filter.type === 'cycle'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="CycleIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					:value="stringFilterValue(filter)"
					size="small"
					:options="cycleOptions"
					placeholder="Select..."
					:loading
					class="w-40!"
					:consistent-menu-width="false"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'priority'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="PriorityIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					:value="stringFilterValue(filter)"
					size="small"
					:options="priorityOptions"
					placeholder="Select..."
					clearable
					class="w-44!"
					:consistent-menu-width="false"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'family'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="FamilyIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					:value="stringFilterValue(filter)"
					size="small"
					:options="familyOptions"
					placeholder="Select..."
					clearable
					filterable
					class="w-50!"
					:consistent-menu-width="false"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'severity'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="SeverityIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					:value="stringFilterValue(filter)"
					size="small"
					:options="severityOptions"
					placeholder="Select..."
					clearable
					class="w-36!"
					:consistent-menu-width="false"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'searchQuery' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="SearchIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-input
					:value="stringFilterValue(filter)"
					autosize
					placeholder="CVE, title, or product..."
					size="small"
					class="min-w-60!"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'kevOnly'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="KevIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<div class="border-color bg-default flex h-7 min-w-28 items-center px-3">
					<n-switch
						:value="booleanFilterValue(filter)"
						size="small"
						checked-value
						:unchecked-value="false"
						@update:value="updateBooleanFilterValue(filter, $event)"
					>
						<template #checked>On</template>
						<template #unchecked>Off</template>
					</n-switch>
				</div>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>
		</div>

		<n-dropdown
			v-if="availableFilters.length"
			placement="bottom-start"
			trigger="click"
			:options="availableFilters"
			@select="addFilter"
		>
			<n-button size="small" dashed>
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				<span v-if="!filters.length">Add filter</span>
			</n-button>
		</n-dropdown>

		<n-button v-if="filters.length && isDirty" size="small" secondary type="primary" @click="submit()">
			Submit
		</n-button>

		<n-button v-if="filters.length" size="small" quaternary @click="reset()">Reset</n-button>
	</div>
</template>

<script setup lang="ts">
import type { PatchTuesdayFilterType, PatchTuesdayListFilter } from "./types"
import _cloneDeep from "lodash/cloneDeep"
import _isEqual from "lodash/isEqual"
import { NButton, NDropdown, NInput, NInputGroup, NInputGroupLabel, NSelect, NSwitch, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { PriorityLevel } from "@/types/patch-tuesday"

const props = defineProps<{
	cycles: string[]
	families: string[]
	loading?: boolean
}>()

const emit = defineEmits<{
	(e: "submit", value: PatchTuesdayListFilter[]): void
}>()

const SearchIcon = "carbon:search"
const CycleIcon = "carbon:calendar"
const PriorityIcon = "carbon:warning-hex"
const FamilyIcon = "carbon:category"
const SeverityIcon = "carbon:warning"
const KevIcon = "carbon:security"
const AddIcon = "carbon:add"
const DelIcon = "carbon:delete"

const message = useMessage()

const typeOptions: { label: string; value: PatchTuesdayFilterType }[] = [
	{ label: "Cycle", value: "cycle" },
	{ label: "Priority", value: "priority" },
	{ label: "Product Family", value: "family" },
	{ label: "Severity", value: "severity" },
	{ label: "Search", value: "searchQuery" },
	{ label: "KEV only", value: "kevOnly" }
]

const priorityOptions = [
	{ label: "P0 - Emergency", value: PriorityLevel.P0 },
	{ label: "P1 - High", value: PriorityLevel.P1 },
	{ label: "P2 - Medium", value: PriorityLevel.P2 },
	{ label: "P3 - Low", value: PriorityLevel.P3 }
]

const severityOptions = [
	{ label: "Critical", value: "critical" },
	{ label: "Important", value: "important" },
	{ label: "Moderate", value: "moderate" },
	{ label: "Low", value: "low" }
]

const filters = ref<PatchTuesdayListFilter[]>([])
const lastFilters = ref<PatchTuesdayListFilter[]>([])

const cycleOptions = computed(() => props.cycles.map(cycle => ({ label: cycle, value: cycle })))

const familyOptions = computed(() => props.families.map(family => ({ label: family, value: family })))

const availableFilters = computed(() =>
	typeOptions
		.filter(option => !filters.value.some(filter => filter.type === option.value))
		.map(option => ({ key: option.value, label: option.label }))
)

const isDirty = computed(() => !_isEqual(filters.value, lastFilters.value))

function getFilterLabel(type: PatchTuesdayFilterType): string {
	return typeOptions.find(option => option.value === type)?.label || type
}

function stringFilterValue(filter: PatchTuesdayListFilter): string | null {
	return typeof filter.value === "string" ? filter.value : null
}

function updateStringFilterValue(filter: PatchTuesdayListFilter, value: string | null) {
	filter.value = value
}

function booleanFilterValue(filter: PatchTuesdayListFilter): boolean {
	return filter.value === true
}

function updateBooleanFilterValue(filter: PatchTuesdayListFilter, value: boolean) {
	filter.value = value
}

function defaultValueForType(type: PatchTuesdayFilterType): string | boolean | null {
	if (type === "kevOnly") return true
	if (type === "searchQuery") return ""
	return null
}

function addFilter(key: PatchTuesdayFilterType) {
	if (key === "cycle" && !props.cycles.length) {
		message.warning("No cycles available yet.")
		return
	}

	if (key === "family" && !props.families.length) {
		message.warning("No product families available yet.")
		return
	}

	filters.value.push({ type: key, value: defaultValueForType(key) })
}

function delFilter(key: PatchTuesdayFilterType) {
	filters.value = filters.value.filter(filter => filter.type !== key)
	submit()
}

function setFilter(newFilters: PatchTuesdayListFilter[]) {
	for (const newFilter of newFilters) {
		const filterIndex = filters.value.findIndex(filter => filter.type === newFilter.type)

		if (filterIndex !== -1) {
			if (newFilter.value !== null && newFilter.value !== "" && filters.value[filterIndex]) {
				filters.value[filterIndex].value = newFilter.value
			} else {
				delFilter(newFilter.type)
			}
		} else if (newFilter.value !== null && newFilter.value !== "") {
			filters.value.push(newFilter)
		}
	}
	submit()
}

function reset() {
	filters.value = []
	submit()
}

function submit() {
	lastFilters.value = _cloneDeep(filters.value)
	emit("submit", lastFilters.value)
}

defineExpose({ setFilter })
</script>
