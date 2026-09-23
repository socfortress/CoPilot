<template>
	<VChart
		v-if="points.length"
		class="w-full"
		autoresize
		:option
		:style="{ height: `${height}px`, width: '100%' }"
		role="img"
		:aria-label="`Requests per hour over the last ${points.length} hours, peak ${peak.toLocaleString()}`"
	/>
	<n-empty v-else description="No traffic in the last 24 hours" class="justify-center" :style="{ height: `${height}px` }" />
</template>

<script setup lang="ts">
// Requests per hour, last 24h — one series, so no legend box: the card title names it.
// Specs: 2px line, 10% area wash of the same hue, hairline recessive grid, crosshair
// tooltip. Height goes in :style because vue-echarts sets height:100% inline.
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import VChart from "vue-echarts"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
import { useWafChartColors } from "./chart-colors"

const { points, height = 220 } = defineProps<{
	points: { hour: string; count: number }[]
	height?: number
}>()

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const theme = useThemeStore()
const { markColor } = useWafChartColors()

const peak = computed(() => Math.max(0, ...points.map(p => p.count)))

const option = computed((): ComposeOption<LineSeriesOption | GridComponentOption | TooltipComponentOption> => {
	const style = theme.style
	const muted = style["fg-secondary-color"]
	const hairline = style["border-color"]
	const font = style["font-family"]
	const color = markColor.value

	return {
		backgroundColor: "transparent",
		grid: { left: 8, right: 16, top: 12, bottom: 4, outerBoundsMode: "same", outerBoundsContain: "axisLabel" },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: { type: "line", lineStyle: { color: muted, width: 1 } },
			formatter: params => {
				const p = Array.isArray(params) ? params[0] : params
				const point = points[p?.dataIndex ?? 0]
				if (!point) return ""
				const when = dayjs(point.hour)
				return `<div style="color:${muted};font-size:11px">${when.format("ddd D MMM, HH:mm")}–${when.add(1, "hour").format("HH:mm")}</div>
					<div style="display:flex;align-items:center;gap:6px;margin-top:2px">
						<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
						<b style="font-variant-numeric:tabular-nums">${point.count.toLocaleString()}</b> requests
					</div>`
			}
		},
		xAxis: {
			type: "category",
			boundaryGap: false,
			data: points.map(p => dayjs(p.hour).format("HH:mm")),
			axisLine: { lineStyle: { color: hairline } },
			axisTick: { show: false },
			axisLabel: { color: muted, fontFamily: font, fontSize: 11, interval: 5, hideOverlap: true }
		},
		yAxis: {
			type: "value",
			splitNumber: 3,
			axisLabel: { color: muted, fontFamily: font, fontSize: 11, formatter: (v: number) => v.toLocaleString() },
			splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" } }
		},
		series: [
			{
				type: "line",
				name: "Requests",
				data: points.map(p => p.count),
				smooth: 0.25,
				symbol: "circle",
				symbolSize: 8,
				showSymbol: false,
				lineStyle: { width: 2, color, cap: "round", join: "round" },
				itemStyle: { color, borderColor: style["bg-default-color"], borderWidth: 2 },
				areaStyle: { color, opacity: 0.1 },
				emphasis: { focus: "none", scale: false }
			}
		]
	}
})
</script>
