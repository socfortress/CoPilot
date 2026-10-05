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

			<div class="day-strip bg-secondary relative h-6 overflow-hidden rounded-sm" :title="stripTitle(day)">
				<span
					v-for="hour of HOUR_TICKS"
					:key="hour"
					class="tick absolute"
					:class="hour % 6 === 0 ? 'is-major inset-y-0' : 'inset-y-1.5'"
					:style="{ left: `${(hour / 24) * 100}%` }"
				/>
				<span
					v-for="(window, index) of week[day]"
					:key="index"
					class="window absolute inset-y-0.5 flex items-center justify-center overflow-hidden"
					:style="spanStyle(window)"
					:title="`${window[0]}–${window[1]}`"
					:data-testid="`calendar-window-${day}-${index}`"
				>
					<span class="window-label">{{ windowLabel(window) }}</span>
				</span>
			</div>

			<div class="flex min-w-0 flex-col items-start gap-1.5">
				<span v-if="!week[day].length" class="text-tertiary text-xs">Closed</span>
				<div
					v-for="(window, index) of week[day]"
					:key="index"
					class="flex items-center gap-2"
					:data-testid="`calendar-range-${day}-${index}`"
				>
					<!-- One working window: from → to, its remove control inside the same capsule. -->
					<div class="time-range" :class="{ 'is-readonly': readonly }">
						<n-time-picker
							:formatted-value="window[0]"
							value-format="HH:mm"
							format="HH:mm"
							size="small"
							:bordered="false"
							:show-icon="false"
							:minutes="15"
							:disabled="readonly"
							:actions="null"
							:theme-overrides="COMPACT_INPUT"
							class="time-input"
							:aria-label="`${WEEKDAY_LABEL[day]} window ${index + 1} start`"
							@update:formatted-value="value => setTime(day, index, 0, value)"
						/>
						<Icon name="carbon:arrow-right" :size="12" class="text-tertiary shrink-0" />
						<n-time-picker
							:formatted-value="window[1]"
							value-format="HH:mm"
							format="HH:mm"
							size="small"
							:bordered="false"
							:show-icon="false"
							:minutes="15"
							:disabled="readonly"
							:actions="null"
							:theme-overrides="COMPACT_INPUT"
							class="time-input"
							:aria-label="`${WEEKDAY_LABEL[day]} window ${index + 1} end`"
							@update:formatted-value="value => setTime(day, index, 1, value)"
						/>
						<button
							v-if="!readonly && week[day].length > 1"
							type="button"
							class="range-remove"
							:aria-label="`Remove ${WEEKDAY_LABEL[day]} window ${index + 1}`"
							:title="`Remove ${window[0]}–${window[1]}`"
							:data-testid="`calendar-remove-${day}-${index}`"
							@click="removeWindow(day, index)"
						>
							<Icon name="carbon:close" :size="12" />
						</button>
					</div>
					<span class="text-tertiary font-mono text-[11px] tabular-nums">{{ windowDuration(window) }}</span>
					<button
						v-if="!readonly && index === week[day].length - 1"
						type="button"
						class="range-add"
						:aria-label="`Add a ${WEEKDAY_LABEL[day]} window`"
						:data-testid="`calendar-add-${day}`"
						@click="addWindow(day)"
					>
						<Icon name="carbon:add" :size="12" />
						Window
					</button>
				</div>
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
import { NSwitch, NTimePicker } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { TONE_COLOR } from "../utils"
import { dayError, DEFAULT_WINDOW, nextWindow, WEEKDAY_LABEL, WEEKDAYS, windowSpan } from "./calendar"

const { readonly = false } = defineProps<{ readonly?: boolean }>()

const week = defineModel<Record<Weekday, WorkingWindow[]>>({ required: true })

const SCALE = [0, 6, 12, 18, 24]
/** Time inputs sized to sit two to a capsule: shorter and smaller than Naive's "small". */
const COMPACT_INPUT = {
	peers: {
		Input: {
			heightSmall: "24px",
			fontSizeSmall: "12px",
			paddingSmall: "0 4px",
			// The capsule is the field: the inputs inside it carry no fill of their own.
			color: "transparent",
			colorFocus: "transparent",
			colorDisabled: "transparent"
		}
	}
}

/** A faint tick every hour on the strip, a stronger one every six. */
const HOUR_TICKS = Array.from({ length: 23 }, (_, i) => i + 1)

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

/** "09–12" on a window wide enough to carry it, the full times on a wide one, nothing on a sliver. */
function windowLabel(window: WorkingWindow) {
	const span = windowSpan(window)
	if (!span) return ""
	const hours = (span.width / 100) * 24
	if (hours >= 6) return `${window[0]}–${window[1]}`
	if (hours >= 3) return `${window[0].replace(/:00$/, "")}–${window[1].replace(/:00$/, "")}`
	return ""
}

/** How long a window lasts: "8h", "1h 30m", "45m"; nothing for an invalid one. */
function windowDuration(window: WorkingWindow) {
	const span = windowSpan(window)
	if (!span) return ""
	const minutes = Math.round((span.width / 100) * 24 * 60)
	const hours = Math.floor(minutes / 60)
	const rest = minutes % 60
	return hours ? (rest ? `${hours}h ${rest}m` : `${hours}h`) : `${rest}m`
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
	opacity: 0.45;
}

.day-strip .tick.is-major {
	opacity: 1;
}

/* Each working window is a solid block cut out of the track by a ring of the track's own
   colour, so two windows that meet (a lunch break) still read as two. */
.day-strip .window {
	background-color: var(--primary-color);
	border-radius: 3px;
	box-shadow:
		0 0 0 1px var(--bg-secondary-color),
		inset 0 1px 0 rgb(255 255 255 / 0.28);
	transition: filter 0.15s;
}

.day-strip .window:hover {
	filter: brightness(1.12);
}

.day-strip .window-label {
	padding: 0 4px;
	font-family: var(--font-family-mono);
	font-size: 10px;
	font-weight: 600;
	line-height: 1;
	white-space: nowrap;
	/* Dark ink on the brand yellow, in both themes. */
	color: rgb(0 0 0 / 0.78);
}

.is-closed .day-strip {
	opacity: 0.5;
}

/* A window's capsule: from → to, and its remove control behind a hairline. */
.time-range {
	display: inline-flex;
	align-items: center;
	gap: 2px;
	height: 28px;
	padding: 0 2px 0 4px;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background-color: var(--bg-secondary-color);
	transition: border-color 0.15s;
}

.time-range:focus-within {
	border-color: var(--primary-color);
}

.time-range.is-readonly {
	padding-right: 4px;
}

.time-input {
	width: 50px;
}

.time-input :deep(.n-input__input-el) {
	text-align: center;
	font-family: var(--font-family-mono);
	font-variant-numeric: tabular-nums;
}

.range-remove {
	display: grid;
	place-items: center;
	width: 22px;
	height: 22px;
	margin-left: 2px;
	border-left: 1px solid var(--border-color);
	color: var(--fg-tertiary-color);
	transition: color 0.15s;
}

.range-remove:hover,
.range-remove:focus-visible {
	color: var(--error-color);
}

/* Adding is a different act from removing: outside the capsule, dashed, worded. */
.range-add {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	height: 24px;
	padding: 0 8px;
	border: 1px dashed var(--border-color);
	border-radius: 6px;
	font-size: 12px;
	color: var(--fg-secondary-color);
	transition:
		color 0.15s,
		border-color 0.15s;
}

.range-add:hover,
.range-add:focus-visible {
	border-color: var(--primary-color);
	color: var(--primary-color);
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
