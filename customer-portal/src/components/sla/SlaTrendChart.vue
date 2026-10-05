<template>
	<VChart
		class="w-full"
		:style="{ height }"
		autoresize
		:option="chartOption"
		role="img"
		:aria-label
		data-testid="sla-trend-chart"
	/>
</template>

<script setup lang="ts">
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, TitleComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { SlaOverview, SlaTrendPoint } from "@/types/sla"
import { colord } from "colord"
import { LineChart } from "echarts/charts"
import { GridComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed } from "vue"
import VChart from "vue-echarts"
import {
	buildChartTooltipGlassBase,
	CHART_GRID_CONTAIN_AXIS_LABELS,
	chartTooltipThemeFromStyle,
	formatChartTooltipWithMarker
} from "@/components/common/charts"
import { useThemeStore } from "@/stores/theme"
import { bucketLabel, formatRate } from "./sla"

const { points, bucket, height = "260px" } = defineProps<{
	points: SlaTrendPoint[]
	bucket: SlaOverview["bucket"]
	height?: string
}>()

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, GridComponent])

type ChartOption = ComposeOption<TitleComponentOption | TooltipComponentOption | GridComponentOption | LineSeriesOption>

const themeStore = useThemeStore()

const labels = computed(() => points.map(point => bucketLabel(point.start, bucket)))
const decided = computed(() => points.filter(point => point.rate !== null))
const ariaLabel = computed(() =>
	decided.value.length
		? `Resolution on target per period, from ${formatRate(decided.value[0]!.rate)} to ${formatRate(decided.value.at(-1)!.rate)}`
		: "No resolution outcome in this period"
)

// One measure, one axis: the share of items resolved within target per bucket, 0–100%.
// Volumes travel in the tooltip rather than on a second axis.
const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-secondary-color"]
	const border = style["border-color"]
	const primary = style["primary-color"]
	const fontFamily = style["font-family"]

	if (!decided.value.length) {
		return {
			backgroundColor: "transparent",
			title: {
				text: "No resolution outcome yet",
				left: "center",
				top: "center",
				textStyle: { color: fg, fontSize: 13, fontWeight: "normal", fontFamily }
			}
		}
	}

	return {
		backgroundColor: "transparent",
		grid: { left: 8, right: 16, top: 16, bottom: 8, ...CHART_GRID_CONTAIN_AXIS_LABELS },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: { type: "line", lineStyle: { color: border } },
			formatter: params => {
				const first = Array.isArray(params) ? params[0] : params
				const point = points[first?.dataIndex ?? 0]
				if (!first || !point) return ""
				return formatChartTooltipWithMarker({
					marker: first.marker,
					color: primary,
					title: labels.value[first.dataIndex ?? 0] ?? "",
					lines: [
						`On target: <strong>${formatRate(point.rate)}</strong>`,
						`Opened ${point.opened} · resolved ${point.resolved}`
					]
				})
			}
		},
		xAxis: {
			type: "category",
			data: labels.value,
			boundaryGap: false,
			axisLine: { lineStyle: { color: border } },
			axisTick: { show: false },
			axisLabel: { color: fg, fontSize: 11, hideOverlap: true }
		},
		yAxis: {
			type: "value",
			min: 0,
			max: 100,
			interval: 25,
			axisLabel: { color: fg, fontSize: 10, formatter: "{value}%" },
			splitLine: { lineStyle: { color: border, type: "dashed" } }
		},
		series: [
			{
				name: "On target",
				type: "line",
				data: points.map(point => point.rate),
				connectNulls: false,
				smooth: 0.25,
				symbol: "circle",
				symbolSize: 8,
				showSymbol: points.length <= 31,
				lineStyle: { width: 2, color: primary },
				itemStyle: { color: primary, borderColor: style["bg-default-color"], borderWidth: 2 },
				areaStyle: {
					color: {
						type: "linear",
						x: 0,
						y: 0,
						x2: 0,
						y2: 1,
						colorStops: [
							{ offset: 0, color: colord(primary).alpha(0.22).toRgbString() },
							{ offset: 1, color: colord(primary).alpha(0).toRgbString() }
						]
					}
				}
			}
		]
	}
})
</script>
