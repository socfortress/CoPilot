<template>
	<div class="soc-filter-bar flex flex-wrap items-center gap-2" data-testid="soc-filter-bar">
		<div
			class="period-switch border-default bg-default inline-flex overflow-hidden rounded-md border"
			role="radiogroup"
			aria-label="Period"
		>
			<button
				v-for="option of periodOptions"
				:key="option.key"
				type="button"
				role="radio"
				:aria-checked="preset === option.key"
				class="period-option px-3 py-1.5 font-mono text-xs tracking-wider uppercase transition-colors"
				:class="preset === option.key ? 'is-active' : 'text-secondary hover:text-default'"
				:data-testid="`period-${option.key}`"
				@click="choose(option.key)"
			>
				{{ option.label }}
			</button>
		</div>

		<n-date-picker
			v-if="preset === 'custom'"
			:value="pickerValue"
			type="datetimerange"
			size="small"
			clearable
			:is-date-disabled="isFuture"
			class="max-w-96"
			data-testid="period-custom-picker"
			@confirm="onRange"
			@update:value="onRange"
		/>

		<div class="filter-slot w-64" data-testid="filter-customers">
			<n-select
				v-model:value="customerCodes"
				:options="customerOptions"
				:loading="customersLoading"
				multiple
				filterable
				clearable
				size="small"
				max-tag-count="responsive"
				placeholder="All customers"
			/>
		</div>
		<div class="filter-slot w-48" data-testid="filter-severities">
			<n-select
				v-model:value="severities"
				:options="severityOptions"
				multiple
				clearable
				size="small"
				max-tag-count="responsive"
				placeholder="All severities"
			/>
		</div>
		<n-tooltip :disabled="!sources.length">
			<template #trigger>
				<div class="filter-slot w-44" data-testid="filter-sources">
					<n-select
						v-model:value="sources"
						:options="sourceOptions"
						multiple
						clearable
						filterable
						size="small"
						max-tag-count="responsive"
						placeholder="All sources"
					/>
				</div>
			</template>
			Alert sources narrow alert figures only: cases have no source.
		</n-tooltip>
	</div>
</template>

<script setup lang="ts">
// One filter row above everything it scopes: period, customers, severities, sources.
// Every chart and table on the page re-renders against the same slice.
import type { SelectOption } from "naive-ui"
import type { PeriodPreset, PeriodRange } from "./utils"
import type { Severity } from "@/types/soc-management"
import { NDatePicker, NSelect, NTooltip } from "naive-ui"
import { computed } from "vue"
import { isValidRange, PERIOD_PRESETS, SEVERITIES } from "./utils"

const { customRange, range, customerOptions, customersLoading, sourceOptions } = defineProps<{
	customRange: PeriodRange | null
	/** The range in force, to seed the picker when switching to a custom period. */
	range: PeriodRange
	customerOptions: SelectOption[]
	customersLoading?: boolean
	sourceOptions: SelectOption[]
}>()

const emit = defineEmits<{ (e: "customRange", value: PeriodRange): void }>()

const preset = defineModel<PeriodPreset>("preset", { required: true })
const customerCodes = defineModel<string[]>("customerCodes", { required: true })
const severities = defineModel<Severity[]>("severities", { required: true })
const sources = defineModel<string[]>("sources", { required: true })

const periodOptions = [
	...PERIOD_PRESETS.map(p => ({ key: p.key, label: p.label })),
	{ key: "custom" as const, label: "Custom" }
]
const severityOptions = SEVERITIES.map(severity => ({ label: severity, value: severity }))

const pickerValue = computed<[number, number]>(() => {
	const shown = customRange ?? range
	return [shown.from.getTime(), shown.to.getTime()]
})

function choose(key: PeriodPreset) {
	if (key === "custom") {
		// Start the custom period from the window on screen, so nothing jumps.
		emit("customRange", range)
		return
	}
	preset.value = key
}

function onRange(value: [number, number] | null) {
	if (!value) return
	const next = { from: new Date(value[0]), to: new Date(value[1]) }
	if (isValidRange(next)) emit("customRange", next)
}

function isFuture(timestamp: number) {
	return timestamp > Date.now()
}
</script>

<style scoped>
.period-option + .period-option {
	border-left: 1px solid var(--border-color);
}

.period-option.is-active {
	color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.12);
	box-shadow: inset 0 -2px 0 var(--primary-color);
}
</style>
