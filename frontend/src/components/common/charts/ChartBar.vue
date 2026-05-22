<template>
	<VChart
		ref="chartRef"
		class="w-full"
		:style="{ height, width: '100%' }"
		:autoresize="{ onResize: updatePlotSize }"
		:option="chartOption"
		@finished="updatePlotSize"
		@click="onChartClick"
	/>
</template>

<script setup lang="ts">
import type { BarSeriesOption } from "echarts/charts"
import type { GridComponentOption, TitleComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption, ECElementEvent } from "echarts/core"
import { BarChart } from "echarts/charts"
import { GridComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, ref } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"
import { DASHBOARD_CHART_COLORS } from "./chartColors"

const props = withDefaults(
	defineProps<{
		labels?: string[]
		data?: number[]
		height?: string
		monochrome?: boolean
	}>(),
	{
		labels: () => [],
		data: () => [],
		height: "100%"
	}
)

const emit = defineEmits<{
	itemClick: [item: { name: string }]
}>()

use([CanvasRenderer, BarChart, TitleComponent, TooltipComponent, GridComponent])

type ChartOption = ComposeOption<TitleComponentOption | TooltipComponentOption | GridComponentOption | BarSeriesOption>

const TOOLTIP_GLASS_CSS = [
	"backdrop-filter: blur(3px)",
	"-webkit-backdrop-filter: blur(3px)",
	"background-color: rgba(var(--bg-default-color-rgb) / 0.55) !important",
	"border-radius: var(--border-radius)",
	"box-shadow: 0 5px 10px -5px rgba(0,0,0,0.2), 0 5px 20px 0 rgba(0,0,0,0.2)"
].join("; ")

const themeStore = useThemeStore()
const chartRef = ref<InstanceType<typeof VChart> | null>(null)
const chartWidth = ref(0)

function updatePlotSize() {
	chartWidth.value = chartRef.value?.getWidth() ?? 0
}

const yAxisLabelWidth = computed(() => (chartWidth.value === 0 || chartWidth.value >= 1080 ? 200 : 100))

const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const bc = style["border-color"]
	const ff = style["font-family"]
	const palette = props.monochrome ? [DASHBOARD_CHART_COLORS[0]] : DASHBOARD_CHART_COLORS
	const hasData = props.labels.length > 0

	if (!hasData) {
		return {
			backgroundColor: "transparent",
			title: {
				text: "No data",
				left: "center",
				top: "center",
				textStyle: { color: fg, fontSize: 16, fontFamily: ff }
			}
		}
	}

	const barData = props.labels.map((_, i) => ({
		value: Number(props.data[i] ?? 0),
		itemStyle: {
			color: palette[i % palette.length],
			borderRadius: [0, 4, 4, 0]
		}
	}))

	return {
		backgroundColor: "transparent",
		grid: {
			left: 8,
			right: 16,
			top: 8,
			bottom: 8,
			containLabel: true
		},
		tooltip: {
			trigger: "axis",
			axisPointer: { type: "shadow" },
			backgroundColor: "transparent",
			borderColor: style["primary-color"],
			borderWidth: 1,
			textStyle: { color: fg, fontSize: 12, fontFamily: ff },
			extraCssText: TOOLTIP_GLASS_CSS,
			formatter: params => {
				if (!Array.isArray(params) || params.length === 0) return ""
				const p = params[0]
				const raw = Array.isArray(p.value) ? p.value[0] : p.value
				const val = typeof raw === "number" ? raw : 0
				return `${p.name ?? ""}<br/><strong>${val}</strong>`
			}
		},
		xAxis: {
			type: "value",
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: fg, fontSize: 10 },
			splitLine: { lineStyle: { color: bc } }
		},
		yAxis: {
			type: "category",
			data: [...props.labels],
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: {
				color: fg,
				fontSize: 11,
				width: yAxisLabelWidth.value,
				overflow: "truncate"
			},
			splitLine: { show: false }
		},
		series: [
			{
				name: "value",
				type: "bar",
				barWidth: "60%",
				data: barData,
				label: {
					show: true,
					position: "right",
					distance: 5,
					color: "#fff",
					fontSize: 12,
					formatter: params => String(params.value ?? 0)
				},
				emphasis: { focus: "series" }
			}
		]
	}
})

function onChartClick(params: ECElementEvent) {
	if (params.componentType !== "series" || params.dataIndex == null) return
	const name = props.labels[params.dataIndex]
	if (name) emit("itemClick", { name })
}
</script>
