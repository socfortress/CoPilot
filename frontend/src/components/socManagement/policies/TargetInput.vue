<template>
	<div class="target-input flex items-center gap-1" :data-testid="testId">
		<div class="w-20">
			<n-input-number
				:value="amount"
				:min="unit === 'm' ? 1 : 0.25"
				:step="unit === 'm' ? 5 : 1"
				:precision="unit === 'm' ? 0 : undefined"
				:disabled
				:placeholder
				:show-button="false"
				size="small"
				:input-props="{ 'aria-label': `${ariaLabel} amount` }"
				@update:value="setAmount"
			/>
		</div>
		<div class="w-20">
			<n-select
				:value="unit"
				:options="UNIT_OPTIONS"
				:disabled
				size="small"
				:aria-label="`${ariaLabel} unit`"
				@update:value="setUnit"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
// A target in minutes, edited as an amount and a unit (90 m, 4 h, 3 d). An empty amount
// is "no target" (null) — distinct from zero, which the backend rejects.
import type { DurationUnit } from "../utils"
import { NInputNumber, NSelect } from "naive-ui"
import { shallowRef, watch } from "vue"
import { joinMinutes, splitMinutes } from "../utils"

const {
	disabled = false,
	placeholder = "none",
	ariaLabel = "Target",
	testId
} = defineProps<{ disabled?: boolean; placeholder?: string; ariaLabel?: string; testId?: string }>()

const minutes = defineModel<number | null>({ required: true })

const UNIT_OPTIONS = [
	{ label: "min", value: "m" },
	{ label: "h", value: "h" },
	{ label: "d", value: "d" }
]

const amount = shallowRef<number | null>(null)
const unit = shallowRef<DurationUnit>("h")

// Re-split only when the model changes from outside: re-splitting our own write would
// turn "1.5 h" back into "90 min" under the analyst's cursor.
watch(
	minutes,
	value => {
		if (value === joinMinutes(amount.value, unit.value)) return
		const split = splitMinutes(value)
		amount.value = split.value
		if (value != null) unit.value = split.unit
	},
	{ immediate: true }
)

function setAmount(value: number | null) {
	amount.value = value
	minutes.value = joinMinutes(value, unit.value)
}

function setUnit(value: DurationUnit) {
	unit.value = value
	minutes.value = joinMinutes(amount.value, value)
}
</script>
