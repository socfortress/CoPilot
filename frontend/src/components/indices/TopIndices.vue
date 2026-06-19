<template>
	<n-card class="box-border w-full overflow-hidden" title="Top 8 indices size & health" segmented>
		<n-spin class="h-100 overflow-hidden" :show="loading">
			<div class="h-100 max-w-full overflow-hidden">
				<VChart ref="chartRef" class="h-full w-full" autoresize :option="chartOption" />
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import type { PieSeriesOption } from "echarts/charts"
import type { GridComponentOption, LegendComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { IndexStats } from "@/types/indices"
import bytes from "bytes"
import { PieChart } from "echarts/charts"
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import _ from "lodash"
import { NCard, NSpin } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import VChart from "vue-echarts"
import {
	buildChartTooltipGlassBase,
	CHART_COLORS,
	chartTooltipThemeFromStyle,
	formatChartTooltipWithMarker
} from "@/components/common/charts"
import { useThemeStore } from "@/stores/theme"
import { IndexHealth } from "@/types/indices"

const props = defineProps<{
	indices: IndexStats[] | null
}>()

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent, GridComponent])

type ChartOption = ComposeOption<TooltipComponentOption | LegendComponentOption | GridComponentOption | PieSeriesOption>

const { indices } = toRefs(props)

const style = computed(() => useThemeStore().style)
const loading = computed(() => !indices.value)
const chartRef = ref<InstanceType<typeof VChart> | null>(null)

const labelFontSize = computed(() => (window.innerWidth > 1000 ? 13 : 11))

const chartOption = computed((): ChartOption => {
	const list = indices.value ?? []

	const data = _.chain(list)
		.map(i => {
			const item = { ...i }
			if (typeof item.store_size === "string") {
				item.store_size_value = bytes(item.store_size) || undefined
			} else {
				item.store_size_value = item.store_size
			}
			return item
		})
		.orderBy(["store_size"], ["desc"])
		.slice(0, 8)
		.value()

	const green = list.filter(i => i.health === IndexHealth.GREEN).length
	const yellow = list.filter(i => i.health === IndexHealth.YELLOW).length
	const red = list.filter(i => i.health === IndexHealth.RED).length

	const sizeData = data.map(i => ({
		value: i.store_size_value || 0,
		name: i.index
	}))

	const fg = style.value["fg-default-color"]
	const bg = style.value["bg-default-color"]

	const tooltipBase = buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style.value))

	return {
		tooltip: {
			...tooltipBase,
			formatter: params => {
				if (!params || Array.isArray(params)) return ""
				const value = typeof params.value === "number" ? params.value : 0
				const percent = typeof params.percent === "number" ? params.percent : 0
				return formatChartTooltipWithMarker({
					marker: params.marker,
					color: params.color,
					title: params.seriesName ?? "",
					lines: [`${params.name}: <strong>${value}</strong> (${percent}%)`]
				})
			}
		},
		legend: {
			data: sizeData.map(i => i.name),
			left: "left",
			type: "scroll",
			textStyle: { color: fg },
			pageTextStyle: { color: fg }
		},
		grid: {
			top: "0%",
			bottom: "0%",
			height: "80%"
		},
		series: [
			{
				name: "Indices Health",
				top: "-30%",
				zlevel: 1,
				type: "pie",
				radius: [0, "20%"],
				label: { show: false },
				itemStyle: {
					borderColor: bg,
					borderWidth: 2
				},
				data: [
					{ value: green, name: "Green", itemStyle: { color: style.value["success-color"] } },
					{ value: yellow, name: "Yellow", itemStyle: { color: style.value["warning-color"] } },
					{ value: red, name: "Red", itemStyle: { color: style.value["error-color"] } }
				]
			},
			{
				name: "Indices Size",
				type: "pie",
				top: "-20%",
				bottom: "10%",
				color: [...CHART_COLORS],
				tooltip: {
					...tooltipBase,
					formatter: params => {
						if (!params || Array.isArray(params)) return ""
						const value = typeof params.value === "number" ? params.value : 0
						const percent = typeof params.percent === "number" ? params.percent : 0
						return formatChartTooltipWithMarker({
							marker: params.marker,
							color: params.color,
							title: params.seriesName ?? "",
							lines: [`${params.name ?? ""}`, `<strong>${bytes(value)}</strong> (${percent}%)`]
						})
					}
				},

				avoidLabelOverlap: true,
				radius: ["24%", "35%"],
				minAngle: 5,
				zlevel: 2,
				labelLine: {
					length: 25,
					length2: 5,
					showAbove: true,
					lineStyle: {
						width: 1.5,
						type: "dashed"
					}
				},
				label: {
					formatter: "{name|{b}}\n{per|{d}%}",
					minMargin: 10,
					edgeDistance: 10,
					lineHeight: 15,
					rich: {
						name: {
							color: fg,
							fontSize: labelFontSize.value
						},
						per: {
							fontSize: labelFontSize.value,
							fontWeight: "bold",
							color: fg
						}
					}
				},
				labelLayout(params) {
					const chartWidth = chartRef.value?.getWidth() ?? 0
					const points = params.labelLinePoints
					const labelRect = params.labelRect
					if (!points || !labelRect) {
						return {}
					}
					const isLeft = chartWidth > 0 ? labelRect.x < chartWidth / 2 : false
					if (points[2]) {
						points[2][0] = isLeft ? labelRect.x : labelRect.x + labelRect.width
					}
					return {
						labelLinePoints: points,
						hideOverlap: false,
						moverOverlap: "shiftX",
						draggable: true
					}
				},
				itemStyle: {
					borderColor: bg,
					borderWidth: 1
				},
				data: sizeData
			}
		]
	}
})
</script>
