<template>
	<figure
		class="sla-gauge relative m-0 flex flex-col items-center"
		:style="{ width: `${size}px` }"
		data-testid="sla-gauge"
	>
		<svg
			:width="size"
			:height="size"
			:viewBox="`0 0 ${VIEW} ${VIEW}`"
			role="img"
			:aria-label="`${label}: ${formatRate(rate)}, objective ${objective}%`"
		>
			<!-- Dial: a ring of hairline ticks, the instrument's scale. -->
			<g class="gauge-ticks">
				<line
					v-for="tick of ticks"
					:key="tick.angle"
					:x1="tick.x1"
					:y1="tick.y1"
					:x2="tick.x2"
					:y2="tick.y2"
					:stroke-width="tick.major ? 1.5 : 1"
					stroke="var(--border-color)"
				/>
			</g>
			<circle :cx="C" :cy="C" :r="R" fill="none" :stroke="track" :stroke-width="STROKE" />
			<circle
				v-if="rate != null"
				class="gauge-arc"
				:cx="C"
				:cy="C"
				:r="R"
				fill="none"
				:stroke="color"
				:stroke-width="STROKE"
				stroke-linecap="round"
				:stroke-dasharray="`${arc} ${CIRCUMFERENCE}`"
				:transform="`rotate(-90 ${C} ${C})`"
				:style="{ filter: `drop-shadow(0 0 6px color-mix(in srgb, ${color} 55%, transparent))` }"
			/>
			<!-- The objective: a notch on the ring where "good" begins. -->
			<line
				:x1="objectiveMark.x1"
				:y1="objectiveMark.y1"
				:x2="objectiveMark.x2"
				:y2="objectiveMark.y2"
				stroke="var(--fg-secondary-color)"
				stroke-width="2"
				stroke-linecap="round"
			/>
		</svg>
		<div
			class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
			:style="{ height: `${size}px` }"
		>
			<span
				class="inline-flex items-baseline text-4xl leading-none font-semibold"
				:style="{ color: rate == null ? 'var(--fg-tertiary-color)' : undefined }"
				data-testid="sla-gauge-value"
			>
				<span>{{ rate == null ? EMPTY : rate.toFixed(1) }}</span>
				<span v-if="rate != null" class="text-secondary text-lg">%</span>
			</span>
			<span class="text-secondary mt-1.5 font-mono text-[9px] leading-none tracking-wide uppercase">{{ label }}</span>
		</div>
		<figcaption v-if="caption" class="text-tertiary mt-2 text-center text-xs">{{ caption }}</figcaption>
	</figure>
</template>

<script setup lang="ts">
// The page's hero figure: one SLA rate on a dial, with the objective notched on the
// ring. Exactly one per view. The arc's colour is the SLA status, and the number is
// printed in the middle — the colour never stands alone.
import { computed } from "vue"
import { EMPTY, formatRate, RATE_GOOD, rateTone, TONE_COLOR } from "../utils"

const {
	rate,
	label,
	caption,
	size = 176,
	objective = RATE_GOOD
} = defineProps<{
	rate: number | null
	label: string
	caption?: string
	size?: number
	objective?: number
}>()

const VIEW = 200
const C = VIEW / 2
const STROKE = 10
const R = 74
const CIRCUMFERENCE = 2 * Math.PI * R

const color = computed(() => TONE_COLOR[rateTone(rate)])
const track = computed(() =>
	rate == null ? "var(--border-color)" : `color-mix(in srgb, ${color.value} 14%, transparent)`
)
const arc = computed(() => (Math.max(0, Math.min(100, rate ?? 0)) / 100) * CIRCUMFERENCE)

function polar(angleDeg: number, radius: number) {
	const radians = ((angleDeg - 90) * Math.PI) / 180
	return { x: C + radius * Math.cos(radians), y: C + radius * Math.sin(radians) }
}

const ticks = computed(() =>
	Array.from({ length: 60 }, (_, i) => {
		const angle = i * 6
		const major = i % 5 === 0
		const outer = polar(angle, 96)
		const inner = polar(angle, major ? 88 : 91)
		return { angle, major, x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y }
	})
)

const objectiveMark = computed(() => {
	const angle = (objective / 100) * 360
	const outer = polar(angle, R + STROKE / 2 + 3)
	const inner = polar(angle, R - STROKE / 2 - 3)
	return { x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y }
})
</script>

<style scoped>
.gauge-arc {
	transition: stroke-dasharray 0.6s var(--bezier-ease, ease);
}
</style>
