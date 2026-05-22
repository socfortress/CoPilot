<template>
	<VChart
		ref="chartRef"
		class="w-full"
		:style="{ height, width: '100%' }"
		:autoresize="{ onResize: updatePlotWidth }"
		:option="chartOption"
		@finished="updatePlotWidth"
		@click="onChartClick"
	/>
</template>

<script setup lang="ts">
import type { BarSeriesOption } from "echarts/charts"
import type { GridComponentOption, TitleComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { BarChart } from "echarts/charts"
import { GridComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, ref } from "vue"
import VChart from "vue-echarts"
import { useSettingsStore } from "@/stores/settings"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
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
		labelsDatetime?: boolean
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

const GRID_HORIZONTAL_PADDING = 48

const themeStore = useThemeStore()
const dFormats = useSettingsStore().dateFormat
const chartRef = ref<InstanceType<typeof VChart> | null>(null)
const plotWidth = ref(0)

function updatePlotWidth() {
	const chartWidth = chartRef.value?.getWidth() ?? 0
	plotWidth.value = Math.max(0, chartWidth - GRID_HORIZONTAL_PADDING)
}

const categoryLabels = computed(() =>
	props.labels.map(label =>
		props.labelsDatetime ? `${dayjs(label).format(dFormats.date)}\n${dayjs(label).format(dFormats.time)}` : label
	)
)

const showXAxisLabels = computed(() => plotWidth.value === 0 || plotWidth.value >= 500)

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

	const barData = props.labels.map((_, i) => ({
		value: Number(props.data[i] ?? 0),
		itemStyle: {
			color: palette[i % palette.length],
			borderRadius: [4, 4, 0, 0]
		}
	}))

	return {
		backgroundColor: "transparent",
		grid: {
			left: 8,
			right: 8,
			top: 8,
			bottom: showXAxisLabels.value ? 56 : 16,
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
			type: "category",
			data: categoryLabels.value,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: {
				show: showXAxisLabels.value,
				color: fg,
				fontSize: 11,
				interval: "auto",
				hideOverlap: true
			}
		},
		yAxis: {
			type: "value",
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: fg, fontSize: 10 },
			splitLine: { lineStyle: { color: bc } }
		},
		series: [
			{
				name: "value",
				type: "bar",
				barWidth: "60%",
				data: barData,
				emphasis: { focus: "series" }
			}
		]
	}
})

function onChartClick(params: unknown) {
	const p = params as { componentType?: string; dataIndex?: number }
	if (p.componentType !== "series" || p.dataIndex == null) return
	const name = props.labels[p.dataIndex]
	if (name) emit("itemClick", { name })
}
</script>
