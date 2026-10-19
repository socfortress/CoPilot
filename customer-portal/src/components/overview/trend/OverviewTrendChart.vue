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
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, MarkPointComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { TrendDay, TrendEntity } from "./trend"
import { colord } from "colord"
import { BarChart, LineChart } from "echarts/charts"
import { GridComponent, MarkPointComponent, TooltipComponent } from "echarts/components"
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
import { dayLabel, dayTitle, formatNet, TREND_COLORS, trendPeak } from "./trend"

const {
	days,
	entity,
	height = "360px"
} = defineProps<{
	days: TrendDay[]
	entity: TrendEntity
	height?: string
}>()

use([CanvasRenderer, LineChart, BarChart, TooltipComponent, GridComponent, MarkPointComponent])

type ChartOption = ComposeOption<
	TooltipComponentOption | GridComponentOption | MarkPointComponentOption | LineSeriesOption | BarSeriesOption
>

const themeStore = useThemeStore()
const colors = computed(() => TREND_COLORS[themeStore.isThemeDark ? "dark" : "light"])

const ariaLabel = computed(() => {
	const last = days.at(-1)?.[entity]
	const noun = entity === "alerts" ? "alerts" : "cases"
	const open = last?.open === null || last?.open === undefined ? "" : `, ${last.open} still open`
	return `${noun} still open at the end of each day over ${days.length} days, with opened and closed per day${open}`
})

function fade(color: string, alpha: number) {
	return colord(color).alpha(alpha).toRgbString()
}

// Two bands on one calendar: above, how many are still open at the end of each day (a
// level, with its own scale); below, opened up and closed down. Never two scales on one
// axis: each band has its own.
const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const fg2 = style["fg-secondary-color"]
	const border = style["border-color"]
	const surface = style["bg-default-color"]
	const fontFamily = style["font-family"]
	const { opened, closed, open } = colors.value
	const labels = days.map(day => dayLabel(day.day))
	const levels = days.map(day => day[entity].open)
	const last = days.length - 1
	const peak = trendPeak(days, entity)
	const peakIndex = peak ? days.findIndex(day => day.day === peak.day) : -1
	const narrow = days.length <= 7
	const axisName = { color: fg2, fontSize: 10, align: "left" as const, fontFamily }

	function category(gridIndex: number, showLabels: boolean) {
		return {
			type: "category" as const,
			gridIndex,
			data: labels,
			axisLine: { lineStyle: { color: border } },
			axisTick: { show: false },
			axisLabel: { show: showLabels, color: fg2, fontSize: 11, hideOverlap: true }
		}
	}

	const marks: NonNullable<MarkPointComponentOption["data"]> = []
	if (levels[last] !== null && levels[last] !== undefined) {
		// Above the point, like the peak's: beside it, the label sat on the line.
		marks.push({ name: "today", coord: [last, levels[last]], value: levels[last], label: { position: "top" } })
	}
	if (peak && peak.open > 0 && peakIndex !== last) {
		marks.push({ name: "peak", coord: [peakIndex, peak.open], value: `peak ${peak.open}`, label: { position: "top" } })
	}

	return {
		backgroundColor: "transparent",
		animationDuration: 400,
		grid: [
			{ left: 8, right: 28, top: 26, height: "50%", ...CHART_GRID_CONTAIN_AXIS_LABELS },
			{ left: 8, right: 28, top: "72%", bottom: 8, ...CHART_GRID_CONTAIN_AXIS_LABELS }
		],
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: { type: "line", lineStyle: { color: border }, link: [{ xAxisIndex: "all" }] },
			formatter: params => {
				const index = (Array.isArray(params) ? params[0] : params)?.dataIndex ?? 0
				const day = days[index]
				if (!day) return ""
				const counts = day[entity]
				return formatChartTooltipAxisMultiSeries({
					title: dayTitle(day.day),
					rows: [
						{ marker: undefined, color: opened, label: "Opened", valueHtml: String(counts.opened) },
						{ marker: undefined, color: closed, label: "Closed", valueHtml: String(counts.closed) },
						{
							marker: undefined,
							color: "transparent",
							label: "Net",
							valueHtml: formatNet(counts.opened - counts.closed)
						},
						{
							marker: undefined,
							color: open,
							label: "Open at day end",
							valueHtml: counts.open === null ? "—" : String(counts.open)
						}
					]
				})
			}
		},
		// The same category spacing in both bands: each day's point sits above its bars.
		xAxis: [category(0, false), category(1, true)],
		yAxis: [
			{
				type: "value",
				gridIndex: 0,
				min: 0,
				minInterval: 1,
				name: "Open · at day end",
				nameGap: 10,
				nameTextStyle: axisName,
				axisLabel: { color: fg2, fontSize: 10 },
				splitLine: { lineStyle: { color: border, type: "dashed" } }
			},
			{
				type: "value",
				gridIndex: 1,
				minInterval: 1,
				splitNumber: 2,
				name: "Opened ↑  Closed ↓",
				nameGap: 8,
				nameTextStyle: axisName,
				axisLabel: { color: fg2, fontSize: 10, formatter: (value: number) => String(Math.abs(value)) },
				splitLine: { lineStyle: { color: border, type: "dashed" } }
			}
		],
		series: [
			{
				name: "Open",
				type: "line",
				xAxisIndex: 0,
				yAxisIndex: 0,
				data: levels,
				symbol: "circle",
				symbolSize: 6,
				showSymbol: narrow,
				lineStyle: { width: 2, color: open },
				itemStyle: { color: open, borderColor: surface, borderWidth: 2 },
				areaStyle: {
					color: {
						type: "linear",
						x: 0,
						y: 0,
						x2: 0,
						y2: 1,
						colorStops: [
							{ offset: 0, color: fade(open, 0.3) },
							{ offset: 1, color: fade(open, 0.03) }
						]
					}
				},
				markPoint: {
					symbol: "circle",
					symbolSize: 7,
					itemStyle: { color: open, borderColor: surface, borderWidth: 2 },
					label: { show: true, color: fg, fontSize: 11, fontWeight: 600, distance: 6, fontFamily },
					data: marks
				},
				emphasis: { disabled: true }
			},
			{
				name: "Opened",
				type: "bar",
				stack: "flow",
				xAxisIndex: 1,
				yAxisIndex: 1,
				barWidth: narrow ? "24%" : "46%",
				data: days.map(day => day[entity].opened),
				itemStyle: { color: fade(opened, 0.85), borderRadius: [2, 2, 0, 0] },
				emphasis: { disabled: true }
			},
			{
				name: "Closed",
				type: "bar",
				stack: "flow",
				xAxisIndex: 1,
				yAxisIndex: 1,
				data: days.map(day => -day[entity].closed),
				itemStyle: { color: fade(closed, 0.85), borderRadius: [0, 0, 2, 2] },
				emphasis: { disabled: true }
			}
		]
	}
})
</script>
