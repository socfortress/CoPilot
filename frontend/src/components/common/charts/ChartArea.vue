<template>
	<VChart
		ref="chartRef"
		class="w-full"
		:autoresize="{ onResize: updatePlotWidth }"
		:option="chartOption"
		:update-options="{ replaceMerge: ['title', 'series'] }"
		:style="{ height: `${height}px`, width: '100%' }"
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
import { LineChart } from "echarts/charts"
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, ref, toRefs } from "vue"
import VChart from "vue-echarts"
import { useSettingsStore } from "@/stores/settings"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
import { formatBytes } from "@/utils/format"
import {
	buildChartTooltipGlassBase,
	CHART_COLORS,
	chartTooltipThemeFromStyle,
	formatChartTooltipAxisMultiSeriesFromParams
} from "."

interface ChartAreaRow {
	name: string
	values: number[]
}

const props = withDefaults(
	defineProps<{
		title?: string
		labels?: string[]
		data?: number[] | number[][]
		seriesNames?: string[]
		height?: number
		yAxisName?: string
		useFormatBytes?: boolean
		showLegend?: boolean
		labelsDatetime?: boolean
	}>(),
	{
		title: "",
		labels: () => [],
		data: () => [],
		seriesNames: () => [],
		height: 250,
		yAxisName: "",
		useFormatBytes: false,
		showLegend: true,
		labelsDatetime: false
	}
)

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

type ChartOption = ComposeOption<
	TitleComponentOption | TooltipComponentOption | LegendComponentOption | GridComponentOption | LineSeriesOption
>

const GRID_HORIZONTAL_PADDING = 80

const { title, labels, data, seriesNames, height, yAxisName, useFormatBytes, showLegend, labelsDatetime } =
	toRefs(props)
const themeStore = useThemeStore()
const dFormats = useSettingsStore().dateFormat
const chartRef = ref<InstanceType<typeof VChart> | null>(null)
const plotWidth = ref(0)

function updatePlotWidth() {
	const chartWidth = chartRef.value?.getWidth() ?? 0
	plotWidth.value = Math.max(0, chartWidth - GRID_HORIZONTAL_PADDING)
}

function isMultiSeriesData(values: number[] | number[][]): values is number[][] {
	return values.length > 0 && Array.isArray(values[0])
}

const chartRows = computed((): ChartAreaRow[] => {
	const axisLabels = labels.value
	const values = data.value

	if (!axisLabels.length || !values.length) return []

	if (isMultiSeriesData(values)) {
		return values.map((row, i) => ({
			name: seriesNames.value[i] ?? `Series ${i + 1}`,
			values: row
		}))
	}

	return [
		{
			name: seriesNames.value[0] ?? "value",
			values
		}
	]
})

const hasData = computed(() => chartRows.value.some(row => row.values.length > 0))

const categoryLabels = computed(() =>
	(labels.value || []).map(label =>
		labelsDatetime.value ? `${dayjs(label).format(dFormats.date)}\n${dayjs(label).format(dFormats.time)}` : label
	)
)

const showXAxisLabels = computed(() => plotWidth.value === 0 || plotWidth.value >= 360)

const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const fgSecondary = style["fg-secondary-color"]
	const border = style["border-color"]
	const ff = style["font-family"]

	if (!hasData.value) {
		return {
			backgroundColor: "transparent",
			title: {
				show: true,
				text: "No data",
				left: "center",
				top: "center",
				textStyle: { color: fg, fontSize: 16, fontFamily: ff }
			},
			series: []
		}
	}

	const eSeries: LineSeriesOption[] = chartRows.value.map((row, i) => ({
		name: row.name,
		type: "line",
		smooth: true,
		symbol: "none",
		lineStyle: { width: 1.5 },
		areaStyle: { opacity: 0.08 },
		itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
		data: row.values
	}))

	const showTitle = Boolean(title.value)
	const showLegendBlock = showLegend.value && chartRows.value.length > 1

	return {
		backgroundColor: "transparent",
		title: showTitle
			? {
					show: true,
					text: title.value,
					textStyle: {
						color: fg,
						fontSize: 13,
						fontWeight: 500,
						fontFamily: ff
					},
					left: 10,
					top: 0
				}
			: { show: false },
		tooltip: {
			...buildChartTooltipGlassBase(
				chartTooltipThemeFromStyle({
					...style,
					"font-family": style["font-family-mono"]
				}),
				{ trigger: "axis" }
			),
			formatter: params =>
				formatChartTooltipAxisMultiSeriesFromParams(params, {
					titleMutedColor: fgSecondary,
					formatTitle: (first: CallbackDataParams) => {
						const idx = first.dataIndex ?? 0
						return categoryLabels.value[idx] ?? ""
					},
					formatRow: (p: CallbackDataParams) => {
						const raw = p.value
						const valueHtml = useFormatBytes.value
							? `${formatBytes(`${raw}`)}`
							: typeof raw === "number"
								? raw.toFixed(2)
								: String(raw ?? "")
						return { label: p.seriesName ?? "", valueHtml }
					}
				})
		},
		legend: showLegendBlock
			? {
					bottom: 0,
					textStyle: { color: fgSecondary, fontSize: 11 },
					icon: "roundRect",
					itemWidth: 12,
					itemHeight: 3
				}
			: undefined,
		grid: {
			left: 10,
			right: 10,
			top: showTitle ? 55 : 16,
			bottom: showLegendBlock
				? 40 + (labelsDatetime.value ? 10 : 0)
				: showXAxisLabels.value
					? 56 + (labelsDatetime.value ? 10 : 0)
					: 16 + (labelsDatetime.value ? 10 : 0)
		},
		xAxis: {
			type: "category",
			data: categoryLabels.value,
			axisLine: { lineStyle: { color: border } },
			axisLabel: {
				show: showXAxisLabels.value,
				color: fgSecondary,
				fontSize: 10,
				interval: "auto",
				hideOverlap: true
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
				formatter: useFormatBytes.value ? (v: number) => `${formatBytes(`${v}`)}` : undefined
			},
			splitLine: { lineStyle: { color: border, opacity: 0.3 } }
		},
		series: eSeries
	}
})
</script>
