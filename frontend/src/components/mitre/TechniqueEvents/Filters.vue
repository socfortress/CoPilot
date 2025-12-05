<template>
	<div class="flex flex-wrap gap-3">
		<div>
			<n-popover placement="top-start" trigger="click" overlap>
				<template #trigger>
					<n-badge :show="!!mitreField" dot type="success" :offset="[0, 6]">
						<n-button size="small" secondary class="px-2!">
							<template #icon>
								<Icon :name="ConfigIcon" :size="16" />
							</template>
						</n-button>
					</n-badge>
				</template>

				<div class="pt-1 pb-2">
					<div class="text-secondary mb-1 text-sm">Mitre field:</div>
					<n-input v-model:value="mitreField" size="small" clearable class="w-40!" />
				</div>
			</n-popover>
		</div>
		<div>
			<n-input-group>
				<n-select
					v-model:value="filterTimeRange.unit"
					:options="unitOptions"
					placeholder="Time unit"
					size="small"
					class="w-24!"
				/>
				<n-input-number
					v-model:value="filterTimeRange.value"
					:min="1"
					placeholder="Value"
					class="w-26!"
					size="small"
					:parse="parseTimeValue"
				/>
			</n-input-group>
		</div>
		<div v-for="filter of usedFilters" :key="filter.type">
			<n-input-group>
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-input v-model:value="filter.value" autosize placeholder="Input..." size="small" class="min-w-30!" />
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
				Add filter
			</n-button>
		</n-dropdown>
	</div>
</template>

<script setup lang="ts">
import _toSafeInteger from "lodash/toSafeInteger"
import {
	NBadge,
	NButton,
	NDropdown,
	NInput,
	NInputGroup,
	NInputGroupLabel,
	NInputNumber,
	NPopover,
	NSelect
} from "naive-ui"
import { computed, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "update", value: { type: string; value: string }[]): void
}>()

const usedFilters = ref<{ type: string; value: string | null }[]>([{ type: "index_pattern", value: "wazuh-*" }])

const filterTimeRange = ref({
	unit: "h",
	value: 24
})

const mitreField = ref<string | null>(null)

const unitOptions: { label: string; value: "h" | "d" | "w" }[] = [
	{ label: "Hours", value: "h" },
	{ label: "Days", value: "d" },
	{ label: "Weeks", value: "w" }
]

const proxyFilters = computed<{ type: string; value: string }[]>(() => {
	const filters = [
		{ type: "time_range", value: `now-${filterTimeRange.value.value}${filterTimeRange.value.unit}` },
		...usedFilters.value.filter(o => !!o.value)
	] as { type: string; value: string }[]

	if (mitreField.value) {
		filters.push({ type: "mitre_field", value: mitreField.value })
	}

	return filters
})

const ConfigIcon = "carbon:settings"
const AddIcon = "carbon:add"
const DelIcon = "carbon:delete"

const typeOptions: { label: string; value: string }[] = [
	{ label: "Rule level", value: "rule_level" },
	{ label: "Rule group", value: "rule_group" },
	{ label: "Index pattern", value: "index_pattern" }
]

const availableFilters = computed(() =>
	typeOptions
		.filter(o => !usedFilters.value.map(o => o.type).includes(o.value))
		.map(t => ({ key: t.value, label: t.label }))
)

function getFilterLabel(type: string): string {
	return typeOptions.find(o => o.value === type)?.label || type
}

function addFilter(key: string) {
	usedFilters.value.push({ type: key, value: null })
}

function delFilter(key: string) {
	usedFilters.value = usedFilters.value.filter(o => o.type !== key)
}

function parseTimeValue(input: string) {
	return _toSafeInteger(input) || 1
}

watch(
	proxyFilters,
	val => {
		emit("update", val)
	},
	{
		deep: true,
		immediate: true
	}
)
</script>
