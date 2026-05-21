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
import type { TimeSeriesData } from "@/types/metrics.d"
import { LineChart } from "echarts/charts"
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, ref, toRefs } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"

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

const COLORS = ["#38bdf8", "#22c55e", "#eab308", "#ef4444", "#a855f7", "#f97316", "#06b6d4", "#ec4899"] as const

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
		itemStyle: { color: COLORS[i % COLORS.length] },
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
			top: 5
		},
		tooltip: {
			trigger: "axis",
			backgroundColor: style.value["bg-default-color"],
			borderColor: style.value["primary-color"],
			textStyle: {
				color: fg,
				fontSize: 12,
				fontFamily: style.value["font-family-mono"]
			},
			formatter(params) {
				if (!Array.isArray(params) || params.length === 0) return ""
				const first = params[0]
				const time = Array.isArray(first.value) ? first.value[0] : null
				let html = `<div style="font-size:11px;color:${fgSecondary};margin-bottom:4px">${time != null ? new Date(time).toLocaleString() : ""}</div>`
				for (const p of params) {
					const raw = Array.isArray(p.value) ? p.value[1] : p.value
					const val = formatBytes.value
						? fmtBytes(Number(raw))
						: typeof raw === "number"
							? raw.toFixed(2)
							: String(raw ?? "")
					html += `<div>${p.marker} ${p.seriesName}: <b>${val}</b></div>`
				}
				return html
			}
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
			top: 35,
			bottom: seriesNames.length > 1 ? 40 : 20
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
