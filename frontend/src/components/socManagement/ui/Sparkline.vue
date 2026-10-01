<template>
	<svg
		v-if="points.length > 1"
		class="sparkline shrink-0"
		:width
		:height
		:viewBox="`0 0 ${width} ${height}`"
		role="img"
		:aria-label="`Trend over ${values.length} periods, peak ${peak}`"
	>
		<path :d="area" :fill="markColor" fill-opacity="0.12" />
		<polyline
			:points="line"
			fill="none"
			:stroke="markColor"
			stroke-width="1.5"
			stroke-linejoin="round"
			stroke-linecap="round"
		/>
		<circle
			:cx="last.x"
			:cy="last.y"
			r="2.5"
			:fill="markColor"
			stroke="var(--bg-default-color)"
			stroke-width="1.5"
		/>
	</svg>
</template>

<script setup lang="ts">
// A one-series trend in the row it belongs to: no axes, the last value marked.
import { computed } from "vue"
import { useSocChartColors } from "../charts/chart-colors"

const { values, width = 88, height = 24 } = defineProps<{ values: number[]; width?: number; height?: number }>()

const { primary: markColor } = useSocChartColors()

const PAD = 3
const peak = computed(() => Math.max(0, ...values))
const points = computed(() => {
	const span = Math.max(1, values.length - 1)
	const top = Math.max(1, peak.value)
	return values.map((value, i) => ({
		x: PAD + (i / span) * (width - PAD * 2),
		y: height - PAD - (value / top) * (height - PAD * 2)
	}))
})
const line = computed(() => points.value.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" "))
const area = computed(() => {
	const first = points.value[0]
	const end = points.value[points.value.length - 1]
	return `M${first.x},${height - PAD} L${line.value.replaceAll(" ", " L")} L${end.x},${height - PAD} Z`
})
const last = computed(() => points.value[points.value.length - 1])
</script>
