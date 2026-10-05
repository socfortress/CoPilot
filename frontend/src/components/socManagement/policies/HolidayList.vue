<template>
	<div class="flex flex-col gap-2" data-testid="calendar-holidays">
		<div v-if="!readonly" class="flex items-center gap-2">
			<n-date-picker
				v-model:formatted-value="pending"
				type="date"
				value-format="yyyy-MM-dd"
				size="small"
				clearable
				placeholder="Add a holiday"
				class="max-w-48"
				data-testid="calendar-holiday-picker"
			/>
			<n-button size="small" secondary :disabled="!pending" data-testid="calendar-holiday-add" @click="add">
				<template #icon><Icon name="carbon:add" :size="14" /></template>
				Add
			</n-button>
		</div>
		<div v-if="holidays.length" class="flex flex-wrap gap-1.5">
			<n-tag
				v-for="day of holidays"
				:key="day"
				size="small"
				:closable="!readonly"
				:bordered="false"
				class="font-mono"
				:data-testid="`calendar-holiday-${day}`"
				@close="remove(day)"
			>
				{{ label(day) }}
			</n-tag>
		</div>
		<div v-else class="text-tertiary min-h-5.5 text-xs">No holidays: every working day counts.</div>
	</div>
</template>

<script setup lang="ts">
// Closed days on top of the weekly schedule. Dates are local to the calendar's timezone
// (a holiday is a day in the customer's country, not a UTC day).
import dayjs from "dayjs"
import { NButton, NDatePicker, NTag } from "naive-ui"
import { shallowRef } from "vue"
import Icon from "@/components/common/Icon.vue"

const { readonly = false } = defineProps<{ readonly?: boolean }>()

const holidays = defineModel<string[]>({ required: true })

const pending = shallowRef<string | null>(null)

function add() {
	if (!pending.value) return
	holidays.value = [...new Set([...holidays.value, pending.value])].sort()
	pending.value = null
}

function remove(day: string) {
	holidays.value = holidays.value.filter(item => item !== day)
}

function label(day: string) {
	return dayjs(day).format("ddd DD MMM YYYY")
}
</script>
