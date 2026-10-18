<template>
	<VChart
		class="w-full"
		:style="{ height }"
		autoresize
		:option="chartOption"
		role="img"
		:aria-label
		data-testid="overview-trend-chart"
	/>
</template>

<script setup lang="ts">
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { TrendDay, TrendEntity } from "./trend"
import { LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed } from "vue"
import VChart from "vue-echarts"
import {
	buildChartTooltipGlassBase,
	CHART_GRID_CONTAIN_AXIS_LABELS,
	chartTooltipThemeFromStyle,
	formatChartTooltipAxisMultiSeries
} from "@/components/common/charts"
import { useThemeStore } from "@/stores/theme"
import { dayLabel, dayTitle, formatNet, TREND_COLORS, trendTotals } from "./trend"

const {
	days,
	entity,
	height = "240px"
} = defineProps<{
	days: TrendDay[]
	entity: TrendEntity
	height?: string
}>()

use([CanvasRenderer, LineChart, TooltipComponent, GridComponent])

type ChartOption = ComposeOption<TooltipComponentOption | GridComponentOption | LineSeriesOption>

const themeStore = useThemeStore()
const colors = computed(() => TREND_COLORS[themeStore.isThemeDark ? "dark" : "light"])

const ariaLabel = computed(() => {
	const { opened, closed } = trendTotals(days, entity)
	return `${entity === "alerts" ? "Alerts" : "Cases"} opened and closed per day over ${days.length} days: ${opened} opened, ${closed} closed`
})

// Two measures of one kind (items per day) on one axis. The legend is the panel's
// figures above the chart, each with its line's colour beside it.
const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-secondary-color"]
	const border = style["border-color"]
	const surface = style["bg-default-color"]
	const showSymbol = days.length <= 7

	function line(name: string, color: string, values: number[]): LineSeriesOption {
		return {
			name,
			type: "line",
			data: values,
			symbol: "circle",
			symbolSize: 8,
			showSymbol,
			lineStyle: { width: 2, color },
			itemStyle: { color, borderColor: surface, borderWidth: 2 },
			emphasis: { focus: "none", scale: false }
		}
	}

	return {
		backgroundColor: "transparent",
		animationDuration: 400,
		grid: { left: 8, right: 16, top: 12, bottom: 8, ...CHART_GRID_CONTAIN_AXIS_LABELS },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: { type: "line", lineStyle: { color: border } },
			formatter: params => {
				const index = (Array.isArray(params) ? params[0] : params)?.dataIndex ?? 0
				const day = days[index]
				if (!day) return ""
				const { opened, closed } = day[entity]
				return formatChartTooltipAxisMultiSeries({
					title: dayTitle(day.day),
					rows: [
						{ marker: undefined, color: colors.value.opened, label: "Opened", valueHtml: String(opened) },
						{ marker: undefined, color: colors.value.closed, label: "Closed", valueHtml: String(closed) },
						{ marker: undefined, color: "transparent", label: "Net", valueHtml: formatNet(opened - closed) }
					]
				})
			}
		},
		xAxis: {
			type: "category",
			data: days.map(day => dayLabel(day.day)),
			boundaryGap: false,
			axisLine: { lineStyle: { color: border } },
			axisTick: { show: false },
			axisLabel: { color: fg, fontSize: 11, hideOverlap: true }
		},
		yAxis: {
			type: "value",
			minInterval: 1,
			axisLabel: { color: fg, fontSize: 10 },
			splitLine: { lineStyle: { color: border, type: "dashed" } }
		},
		series: [
			line(
				"Opened",
				colors.value.opened,
				days.map(day => day[entity].opened)
			),
			line(
				"Closed",
				colors.value.closed,
				days.map(day => day[entity].closed)
			)
		]
	}
})
</script>
