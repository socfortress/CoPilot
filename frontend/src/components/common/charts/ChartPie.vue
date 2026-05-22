<template>
	<VChart class="w-full" :style="{ height, width: '100%' }" autoresize :option="chartOption" @click="onChartClick" />
</template>

<script setup lang="ts">
import type { PieSeriesOption } from "echarts/charts"
import type { LegendComponentOption, TitleComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption, ECElementEvent } from "echarts/core"
import { PieChart } from "echarts/charts"
import { GraphicComponent, LegendComponent, TitleComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed } from "vue"
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

use([CanvasRenderer, PieChart, LegendComponent, TooltipComponent, TitleComponent, GraphicComponent])

type ChartOption = ComposeOption<
	TitleComponentOption | TooltipComponentOption | LegendComponentOption | PieSeriesOption
>

const themeStore = useThemeStore()

const pieData = computed(() =>
	props.labels.map((label, i) => ({
		name: label,
		value: Number(props.data[i] ?? 0)
	}))
)

const totalValue = computed(() => pieData.value.reduce((sum, item) => sum + item.value, 0))

const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const ff = style["font-family"]
	const palette = props.monochrome ? [DASHBOARD_CHART_COLORS[0]] : [...DASHBOARD_CHART_COLORS]
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

	return {
		backgroundColor: "transparent",
		// TODO-FE: refactor all echarts palette
		color: palette,
		tooltip: {
			trigger: "item",
			backgroundColor: "transparent",
			borderColor: style["primary-color"],
			borderWidth: 1,
			textStyle: { color: fg, fontSize: 12, fontFamily: ff },
			// TODO-FE: refactor all echarts tooltips
			extraCssText: [
				"backdrop-filter: blur(3px)",
				"-webkit-backdrop-filter: blur(3px)",
				"background-color: rgba(var(--bg-default-color-rgb) / 0.55) !important",
				"border-radius: var(--border-radius)",
				"box-shadow: 0 5px 10px -5px rgba(0,0,0,0.2), 0 5px 20px 0 rgba(0,0,0,0.2)"
			].join("; "),
			formatter: params => {
				if (!params || Array.isArray(params)) return ""
				const val = typeof params.value === "number" ? params.value : 0
				const pct = typeof params.percent === "number" ? params.percent : 0
				return `${params.name ?? ""}<br/><strong>${val}</strong> (${pct.toFixed(1)}%)`
			}
		},
		graphic: [
			{
				type: "text",
				left: "center",
				top: "33%",
				style: {
					text: `Total\n\n${totalValue.value}`,
					fill: fg,
					fontSize: 14,
					fontFamily: ff,
					textAlign: "center",
					textVerticalAlign: "middle"
				}
			}
		],
		legend: {
			show: true,
			selectedMode: false,
			type: "scroll",
			orient: "horizontal",
			bottom: 4,
			left: "center",
			width: "92%",
			textStyle: { color: fg, fontSize: 11, fontFamily: ff },
			pageTextStyle: { color: fg },
			pageIconColor: fg,
			pageIconInactiveColor: style["fg-secondary-color"],
			itemWidth: 7,
			itemHeight: 7,
			itemGap: 16,
			formatter: (name: string) => {
				const item = pieData.value.find(d => d.name === name)
				const val = item?.value ?? 0
				const pct = totalValue.value > 0 ? (val / totalValue.value) * 100 : 0
				return `${name} - ${val} (${pct.toFixed(1)}%)`
			}
		},
		series: [
			{
				name: "value",
				type: "pie",
				radius: ["55%", "75%"],
				center: ["50%", "40%"],
				avoidLabelOverlap: true,
				itemStyle: { borderWidth: 0 },
				label: {
					show: true,
					position: "outside",
					color: fg,
					fontSize: 11,
					fontFamily: ff,
					formatter: params => {
						const pct = typeof params.percent === "number" ? params.percent : 0
						return `${pct.toFixed(1)}%`
					}
				},
				labelLine: { show: true, length: 10, length2: 6 },
				data: pieData.value
			}
		]
	}
})

function resolveClickedItemName(params: ECElementEvent): string | undefined {
	if (params.componentType === "legend" || params.componentType === "series") {
		return params.name ?? props.labels[params.dataIndex ?? -1]
	}
	return undefined
}

function onChartClick(params: ECElementEvent) {
	const name = resolveClickedItemName(params)
	if (name) emit("itemClick", { name })
}
</script>
