<template>
	<VChart
		ref="chartRef"
		class="w-full"
		:autoresize="{ onResize: updatePlotWidth }"
		:option="chartOption"
		:style="{ height: `${height}px` }"
		@finished="updatePlotWidth"
	/>
</template>

<script setup lang="ts">
import type { LineSeriesOption } from "echarts/charts"
import type {
	GridComponentOption,
	LegendComponentOption,
	TitleComponentOption,
	TooltipComponentOption
} from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { CallbackDataParams } from "echarts/types/dist/shared"
import type { TimeSeriesData } from "@/types/metrics.d"
import { LineChart } from "echarts/charts"
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, ref, toRefs } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"
import {
	buildChartTooltipGlassBase,
	CHART_COLORS,
	chartTooltipThemeFromStyle,
	formatChartTooltipAxisMultiSeriesFromParams
} from "../common/charts"

const props = withDefaults(
	defineProps<{
		title: string
		series: TimeSeriesData
		height?: number
		yAxisName?: string
		formatBytes?: boolean
	}>(),
	{
		height: 250,
		yAxisName: "",
		formatBytes: false
	}
)

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

type ChartOption = ComposeOption<
	TitleComponentOption | TooltipComponentOption | LegendComponentOption | GridComponentOption | LineSeriesOption
>

const GRID_HORIZONTAL_PADDING = 80

const { title, series, height, yAxisName, formatBytes } = toRefs(props)
const style = computed(() => useThemeStore().style)
const chartRef = ref<InstanceType<typeof VChart> | null>(null)
const plotWidth = ref(0)

function updatePlotWidth() {
	const chartWidth = chartRef.value?.getWidth() ?? 0
	plotWidth.value = Math.max(0, chartWidth - GRID_HORIZONTAL_PADDING)
}

const xAxisLabelFormatter = computed(() => {
	const compact = plotWidth.value > 0 && plotWidth.value < 360
	return (value: string | number) => {
		const ts = typeof value === "number" ? value : Number(value)
		const d = new Date(ts)
		if (Number.isNaN(d.getTime())) return String(value)
		if (compact) {
			return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
		}
		return d.toLocaleString(undefined, {
			month: "short",
			day: "numeric",
			hour: "2-digit",
			minute: "2-digit"
		})
	}
})

function fmtBytes(bytes: number): string {
	if (bytes === null || bytes === undefined) return "—"
	const units = ["B", "KB", "MB", "GB", "TB"]
	let i = 0
	let v = Number(bytes)
	while (v >= 1024 && i < units.length - 1) {
		v /= 1024
		i++
	}
	return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

const chartOption = computed((): ChartOption => {
	const seriesData = series.value || {}
	const seriesNames = Object.keys(seriesData)
	const fg = style.value["fg-default-color"]
	const fgSecondary = style.value["fg-secondary-color"]
	const border = style.value["border-color"]

	const eSeries: LineSeriesOption[] = seriesNames.map((name, i) => ({
		name,
		type: "line",
		smooth: true,
		symbol: "none",
		lineStyle: { width: 1.5 },
		areaStyle: { opacity: 0.08 },
		itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
		data: (seriesData[name] || []).map(d => [new Date(d.time).getTime(), d.value])
	}))

	return {
		backgroundColor: "transparent",
		title: {
			text: title.value,
			textStyle: {
				color: fg,
				fontSize: 13,
				fontWeight: 500,
				fontFamily: style.value["font-family"]
			},
			left: 10,
			top: 0
		},
		tooltip: {
			...buildChartTooltipGlassBase(
				chartTooltipThemeFromStyle({
					...style.value,
					"font-family": style.value["font-family-mono"]
				}),
				{ trigger: "axis" }
			),
			formatter: params =>
				formatChartTooltipAxisMultiSeriesFromParams(params, {
					titleMutedColor: fgSecondary,
					formatTitle: (first: CallbackDataParams) => {
						const time = Array.isArray(first.value) ? first.value[0] : null
						return time != null ? new Date(time).toLocaleString() : ""
					},
					formatRow: (p: CallbackDataParams) => {
						const raw = Array.isArray(p.value) ? p.value[1] : p.value
						const valueHtml = formatBytes.value
							? fmtBytes(Number(raw))
							: typeof raw === "number"
								? raw.toFixed(2)
								: String(raw ?? "")
						return { label: p.seriesName ?? "", valueHtml }
					}
				})
		},
		legend: {
			bottom: 0,
			textStyle: { color: fgSecondary, fontSize: 11 },
			icon: "roundRect",
			itemWidth: 12,
			itemHeight: 3
		},
		grid: {
			left: 60,
			right: 20,
			top: 55,
			bottom: 40
		},
		xAxis: {
			type: "category",
			axisLine: { lineStyle: { color: border } },
			axisLabel: {
				color: fgSecondary,
				fontSize: 10,
				interval: "auto",
				hideOverlap: true,
				showMinLabel: true,
				showMaxLabel: true,
				formatter: xAxisLabelFormatter.value
			},
			splitLine: { show: false }
		},
		yAxis: {
			type: "value",
			name: yAxisName.value,
			nameTextStyle: { color: fgSecondary, fontSize: 10 },
			axisLine: { lineStyle: { color: border } },
			axisLabel: {
				color: fgSecondary,
				fontSize: 10,
				formatter: formatBytes.value ? (v: number) => fmtBytes(v) : undefined
			},
			splitLine: { lineStyle: { color: border, opacity: 0.3 } }
		},
		series: eSeries
	}
})
</script>
