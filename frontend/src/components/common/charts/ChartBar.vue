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
import {
	buildChartTooltipGlassBase,
	CHART_COLORS,
	chartTooltipThemeFromStyle,
	formatChartTooltipAxisFirst
} from "."

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

const themeStore = useThemeStore()
const chartRef = ref<InstanceType<typeof VChart> | null>(null)
const chartWidth = ref(0)

function updatePlotSize() {
	chartWidth.value = chartRef.value?.getWidth() ?? 0
}

const yAxisLabelWidth = computed(() => (chartWidth.value === 0 || chartWidth.value >= 1080 ? 200 : 100))

const sortedRows = computed(() =>
	props.labels
		.map((label, i) => ({
			label,
			value: Number(props.data[i] ?? 0)
		}))
		.sort((a, b) => b.value - a.value)
)

const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const bc = style["border-color"]
	const ff = style["font-family"]
	const palette = props.monochrome ? [CHART_COLORS[0]] : CHART_COLORS
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

	const barData = sortedRows.value.map((row, i) => ({
		value: row.value,
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
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: { type: "shadow" },
			formatter: params =>
				formatChartTooltipAxisFirst(params, {
					resolveColor: p => {
						const idx = p.dataIndex ?? 0
						return palette[idx % palette.length]
					}
				})
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
			data: sortedRows.value.map(row => row.label),
			inverse: true,
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
	const name = sortedRows.value[params.dataIndex]?.label
	if (name) emit("itemClick", { name })
}
</script>
