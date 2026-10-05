<template>
	<div class="week-schedule flex flex-col" data-testid="week-schedule">
		<div class="hour-scale text-tertiary text-2xs grid items-end font-mono" aria-hidden="true">
			<span />
			<span class="relative h-4">
				<span
					v-for="hour of SCALE"
					:key="hour"
					class="absolute -translate-x-1/2 whitespace-nowrap"
					:style="{ left: `${(hour / 24) * 100}%` }"
				>
					{{ String(hour).padStart(2, "0") }}
				</span>
			</span>
			<span />
		</div>

		<div
			v-for="day of WEEKDAYS"
			:key="day"
			class="day-row border-default grid min-h-11.5 items-center gap-x-3 border-t py-2"
			:class="{ 'is-closed': !week[day].length }"
			:data-testid="`calendar-day-${day}`"
		>
			<div class="flex items-center gap-2">
				<n-switch
					:value="week[day].length > 0"
					size="small"
					:disabled="readonly"
					:aria-label="`${WEEKDAY_LABEL[day]} open`"
					:data-testid="`calendar-open-${day}`"
					@update:value="open => setOpen(day, open)"
				/>
				<span class="text-sm">{{ WEEKDAY_LABEL[day].slice(0, 3) }}</span>
			</div>

			<div class="day-strip bg-secondary relative h-5 overflow-hidden rounded-sm" :title="stripTitle(day)">
				<span
					v-for="hour of [6, 12, 18]"
					:key="hour"
					class="tick absolute inset-y-0"
					:style="{ left: `${(hour / 24) * 100}%` }"
				/>
				<span
					v-for="(window, index) of week[day]"
					:key="index"
					class="window absolute inset-y-1 rounded-xs"
					:style="spanStyle(window)"
				/>
			</div>

			<div class="flex min-w-0 flex-wrap items-center gap-2">
				<span v-if="!week[day].length" class="text-tertiary text-xs">Closed</span>
				<div v-for="(window, index) of week[day]" :key="index" class="window-edit flex items-center gap-1">
					<n-time-picker
						:formatted-value="window[0]"
						value-format="HH:mm"
						format="HH:mm"
						size="small"
						:minutes="15"
						:disabled="readonly"
						:actions="null"
						class="time-input"
						:aria-label="`${WEEKDAY_LABEL[day]} window ${index + 1} start`"
						@update:formatted-value="value => setTime(day, index, 0, value)"
					/>
					<span class="text-tertiary text-xs">–</span>
					<n-time-picker
						:formatted-value="window[1]"
						value-format="HH:mm"
						format="HH:mm"
						size="small"
						:minutes="15"
						:disabled="readonly"
						:actions="null"
						class="time-input"
						:aria-label="`${WEEKDAY_LABEL[day]} window ${index + 1} end`"
						@update:formatted-value="value => setTime(day, index, 1, value)"
					/>
					<n-button
						v-if="!readonly && week[day].length > 1"
						quaternary
						size="tiny"
						:aria-label="`Remove ${WEEKDAY_LABEL[day]} window ${index + 1}`"
						@click="removeWindow(day, index)"
					>
						<template #icon><Icon name="carbon:close" :size="12" /></template>
					</n-button>
				</div>
				<n-button
					v-if="!readonly && week[day].length"
					quaternary
					size="tiny"
					:aria-label="`Add a ${WEEKDAY_LABEL[day]} window`"
					:data-testid="`calendar-add-${day}`"
					@click="addWindow(day)"
				>
					<template #icon><Icon name="carbon:add" :size="14" /></template>
				</n-button>
				<span
					v-if="dayError(week[day])"
					class="inline-flex items-center gap-1 text-xs"
					:style="{ color: TONE_COLOR.bad }"
				>
					<Icon name="carbon:warning-filled" :size="12" />
					{{ dayError(week[day]) }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
// The working week of a calendar: per day, open or closed, and its working windows —
// edited as times and shown as a 24-hour strip, so a lunch break or a late shift reads
// at a glance. Several windows per day are allowed (a lunch break is two of them).
import type { Weekday, WorkingWindow } from "@/types/soc-management"
import { NButton, NSwitch, NTimePicker } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { TONE_COLOR } from "../utils"
import { dayError, DEFAULT_WINDOW, nextWindow, WEEKDAY_LABEL, WEEKDAYS, windowSpan } from "./calendar"

const { readonly = false } = defineProps<{ readonly?: boolean }>()

const week = defineModel<Record<Weekday, WorkingWindow[]>>({ required: true })

const SCALE = [0, 6, 12, 18, 24]

function setDay(day: Weekday, windows: WorkingWindow[]) {
	week.value = { ...week.value, [day]: windows }
}

function setOpen(day: Weekday, open: boolean) {
	setDay(day, open ? [[...DEFAULT_WINDOW]] : [])
}

function setTime(day: Weekday, index: number, edge: 0 | 1, value: string | null) {
	if (!value) return
	setDay(
		day,
		week.value[day].map((window, i) =>
			i === index ? ((edge === 0 ? [value, window[1]] : [window[0], value]) as WorkingWindow) : window
		)
	)
}

function addWindow(day: Weekday) {
	setDay(day, [...week.value[day], nextWindow(week.value[day])])
}

function removeWindow(day: Weekday, index: number) {
	setDay(
		day,
		week.value[day].filter((_, i) => i !== index)
	)
}

function spanStyle(window: WorkingWindow) {
	const span = windowSpan(window)
	return span ? { left: `${span.left}%`, width: `${span.width}%` } : { display: "none" }
}

function stripTitle(day: Weekday) {
	const windows = week.value[day]
	return windows.length ? windows.map(([start, end]) => `${start}–${end}`).join(", ") : "Closed"
}
</script>

<style scoped>
.hour-scale,
.day-row {
	grid-template-columns: 120px minmax(160px, 1fr) minmax(0, 1.4fr);
	column-gap: 0.75rem;
}

.day-strip .tick {
	width: 1px;
	background-color: var(--border-color);
}

.day-strip .window {
	background: linear-gradient(90deg, rgb(var(--primary-color-rgb) / 0.55), rgb(var(--primary-color-rgb) / 0.85));
	box-shadow: 0 0 8px rgb(var(--primary-color-rgb) / 0.35);
}

.is-closed .day-strip {
	opacity: 0.5;
}

.time-input {
	width: 82px;
}

@media (max-width: 900px) {
	.hour-scale {
		display: none;
	}

	.day-row {
		grid-template-columns: 1fr;
		row-gap: 0.5rem;
	}
}
</style>
