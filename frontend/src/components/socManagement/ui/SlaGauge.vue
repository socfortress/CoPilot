<template>
	<figure
		class="sla-gauge relative m-0 flex flex-col items-center"
		:style="{ width: `${size}px` }"
		data-testid="sla-gauge"
	>
		<VChart
			:option
			:style="{ width: `${size}px`, height: `${size}px` }"
			role="img"
			:aria-label="`${label}: ${formatRate(rate)}, objective ${objective}%`"
		/>
		<div
			class="pointer-events-none absolute inset-x-0 top-0 flex flex-col items-center justify-center"
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
// printed in the middle (HTML, so it keeps the page's type) — the colour never stands
// alone. ECharts draws the dial: a ring of hairline ticks as the scale, the track, the
// progress arc from twelve o'clock, and the objective notch.
import type { GaugeSeriesOption } from "echarts/charts"
import type { GraphicComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { GaugeChart } from "echarts/charts"
import { GraphicComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed } from "vue"
import VChart from "vue-echarts"
import { useResolvedColors } from "../charts/chart-colors"
import { EMPTY, formatRate, RATE_GOOD, rateTone } from "../utils"

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

use([CanvasRenderer, GaugeChart, GraphicComponent])

const colors = useResolvedColors()

/** Geometry in a 200-unit box, scaled to `size`: the ring's centre line and thickness. */
const VIEW = 200
const R = 74
const STROKE = 10

const option = computed((): ComposeOption<GaugeSeriesOption | GraphicComponentOption> => {
	const scale = size / VIEW
	const hairline = colors.style.value["border-color"]
	const color = colors.tone(rateTone(rate))
	const dial = { type: "gauge" as const, startAngle: 90, endAngle: -270, min: 0, max: 100, center: ["50%", "50%"] }
	const quiet = {
		pointer: { show: false },
		anchor: { show: false },
		title: { show: false },
		detail: { show: false },
		axisLabel: { show: false }
	}

	// The objective, as a notch across the ring at its angle (clockwise from the top).
	const angle = (objective / 100) * 2 * Math.PI
	const c = size / 2
	const at = (radius: number) => ({ x: c + radius * scale * Math.sin(angle), y: c - radius * scale * Math.cos(angle) })
	const inner = at(R - STROKE / 2 - 3)
	const outer = at(R + STROKE / 2 + 3)

	return {
		backgroundColor: "transparent",
		series: [
			// The scale: 60 hairline ticks outside the ring, a longer one every 30°.
			{
				...dial,
				...quiet,
				radius: "96%",
				splitNumber: 12,
				silent: true,
				animation: false,
				axisLine: { show: false, lineStyle: { width: 0 } },
				progress: { show: false },
				axisTick: { show: true, splitNumber: 5, distance: 0, length: 5 * scale, lineStyle: { color: hairline, width: 1 } },
				splitLine: { show: true, distance: 0, length: 8 * scale, lineStyle: { color: hairline, width: 1.5 } },
				data: [{ value: 0 }]
			},
			// The track and the arc: the rate, coloured by its status.
			{
				...dial,
				...quiet,
				radius: `${R + STROKE / 2}%`,
				silent: true,
				axisTick: { show: false },
				splitLine: { show: false },
				axisLine: {
					lineStyle: {
						width: STROKE * scale,
						color: [[1, rate == null ? hairline : color]],
						opacity: rate == null ? 1 : 0.14
					}
				},
				progress: {
					show: rate != null,
					width: STROKE * scale,
					roundCap: true,
					itemStyle: { color, shadowBlur: 6, shadowColor: color }
				},
				animationDuration: 600,
				data: [{ value: Math.max(0, Math.min(100, rate ?? 0)) }]
			}
		],
		graphic: [
			{
				type: "line",
				silent: true,
				z: 10,
				shape: { x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y },
				style: { stroke: colors.style.value["fg-secondary-color"], lineWidth: 2, lineCap: "round" }
			}
		]
	}
})
</script>
