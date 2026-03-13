<template>
	<div ref="chartEl" :style="{ height: height + 'px' }"></div>
</template>

<script setup lang="ts">
import type { ECharts } from "echarts/core"
import type { TimeSeriesData } from "@/types/metrics.d"
import { BarChart, GaugeChart, LineChart } from "echarts/charts"
import { DataZoomComponent, GridComponent, LegendComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { init as echartsInit, use as echartsUse } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, onBeforeUnmount, onMounted, ref, toRefs, watch } from "vue"
import { useThemeStore } from "@/stores/theme"

echartsUse([
	TitleComponent,
	TooltipComponent,
	LegendComponent,
	GridComponent,
	DataZoomComponent,
	LineChart,
	BarChart,
	GaugeChart,
	CanvasRenderer
])

const COLORS = ["#38bdf8", "#22c55e", "#eab308", "#ef4444", "#a855f7", "#f97316", "#06b6d4", "#ec4899"]

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

const { title, series, height, yAxisName, formatBytes } = toRefs(props)

const chartEl = ref<HTMLElement | null>(null)
const chartCtx = ref<ECharts | null>(null)
const style = computed(() => useThemeStore().style)
let resizeObserver: ResizeObserver | null = null

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

function getOptions() {
	const seriesData = series.value || {}
	const seriesNames = Object.keys(seriesData)

	const eSeries = seriesNames.map((name, i) => ({
		name,
		type: "line" as const,
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
				color: style.value["fg-default-color"],
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
				color: style.value["fg-default-color"],
				fontSize: 12,
				fontFamily: style.value["font-family-mono"]
			},
			formatter(params: any[]) {
				let html = `<div style="font-size:11px;color:${style.value["fg-secondary-color"]};margin-bottom:4px">${new Date(params[0].value[0]).toLocaleString()}</div>`
				params.forEach((p: any) => {
					const val = formatBytes.value
						? fmtBytes(p.value[1])
						: typeof p.value[1] === "number"
							? p.value[1].toFixed(2)
							: p.value[1]
					html += `<div>${p.marker} ${p.seriesName}: <b>${val}</b></div>`
				})
				return html
			}
		},
		legend: {
			bottom: 0,
			textStyle: { color: style.value["fg-secondary-color"], fontSize: 11 },
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
			type: "time",
			axisLine: { lineStyle: { color: style.value["border-color"] } },
			axisLabel: { color: style.value["fg-secondary-color"], fontSize: 10 },
			splitLine: { show: false }
		},
		yAxis: {
			type: "value",
			name: yAxisName.value,
			nameTextStyle: { color: style.value["fg-secondary-color"], fontSize: 10 },
			axisLine: { lineStyle: { color: style.value["border-color"] } },
			axisLabel: {
				color: style.value["fg-secondary-color"],
				fontSize: 10,
				formatter: formatBytes.value ? (v: number) => fmtBytes(v) : undefined
			},
			splitLine: { lineStyle: { color: style.value["border-color"], opacity: 0.3 } }
		},
		series: eSeries
	}
}

function renderChart() {
	if (!chartCtx.value) return
	chartCtx.value.setOption(getOptions(), true)
}

watch([series, style], renderChart)

onMounted(() => {
	if (!chartEl.value) return
	chartCtx.value = echartsInit(chartEl.value)
	renderChart()

	resizeObserver = new ResizeObserver(() => chartCtx.value?.resize())
	resizeObserver.observe(chartEl.value)
})

onBeforeUnmount(() => {
	resizeObserver?.disconnect()
	chartCtx.value?.dispose()
})
</script>
