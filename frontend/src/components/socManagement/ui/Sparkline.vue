<template>
	<VChart
		v-if="values.length > 1"
		class="sparkline shrink-0"
		:option
		:init-options="{ renderer: 'svg' }"
		:style="{ width: `${width}px`, height: `${height}px` }"
		role="img"
		:aria-label="`Trend over ${values.length} periods, peak ${peak}`"
	/>
</template>

<script setup lang="ts">
// A one-series trend in the row it belongs to: no axes, the last value marked. Given
// `labels` (one per value), hovering it shows a small tooltip with the period and the
// value, appended to the body so a table cell cannot clip it. SVG renderer: a table can
// hold a few dozen of these, and a canvas each would cost far more than the line it draws.
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { SVGRenderer } from "echarts/renderers"
import { computed } from "vue"
import VChart from "vue-echarts"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { useThemeStore } from "@/stores/theme"
import { useSocChartColors } from "../charts/chart-colors"

const {
	values,
	labels,
	unit = "",
	width = 88,
	height = 24
} = defineProps<{
	values: number[]
	/** One per value — the period each covers; enables the hover tooltip. */
	labels?: string[]
	/** Appended to the value in the tooltip, e.g. "alerts". */
	unit?: string
	width?: number
	height?: number
}>()

use([SVGRenderer, LineChart, GridComponent, TooltipComponent])

const theme = useThemeStore()
const { primary } = useSocChartColors()

const peak = computed(() => Math.max(0, ...values))

const interactive = computed(() => !!labels && labels.length === values.length)

const option = computed((): ComposeOption<LineSeriesOption | GridComponentOption | TooltipComponentOption> => {
	const color = primary.value
	const style = theme.style
	const lastIndex = values.length - 1
	return {
		backgroundColor: "transparent",
		animation: false,
		grid: { left: 3, right: 3, top: 3, bottom: 3 },
		tooltip: interactive.value
			? {
					...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
					appendToBody: true,
					axisPointer: { type: "line", lineStyle: { color: style["fg-secondary-color"], width: 1 } },
					formatter: params => {
						const point = Array.isArray(params) ? params[0] : params
						const index = point?.dataIndex ?? 0
						const value = values[index] ?? 0
						return `<div data-testid="sparkline-tooltip" style="padding:6px 8px;font-size:12px"><div style="color:${style["fg-secondary-color"]};font-size:11px">${labels?.[index] ?? ""}</div><div style="margin-top:2px"><b style="font-variant-numeric:tabular-nums">${value}</b>${unit ? ` ${unit}` : ""}</div></div>`
					}
				}
			: { show: false },
		xAxis: { type: "category", show: false, boundaryGap: false, data: labels ?? values.map((_, i) => String(i)) },
		yAxis: { type: "value", show: false, min: 0, max: Math.max(1, peak.value) },
		series: [
			{
				type: "line",
				silent: !interactive.value,
				symbol: "none",
				showSymbol: true,
				lineStyle: { width: 1.5, color, cap: "round", join: "round" },
				areaStyle: { color, opacity: 0.12 },
				data: values.map((value, i) =>
					i === lastIndex
						? {
								value,
								symbol: "circle",
								symbolSize: 5,
								itemStyle: { color, borderColor: theme.style["bg-default-color"], borderWidth: 1.5 }
							}
						: value
				)
			}
		]
	}
})
</script>
