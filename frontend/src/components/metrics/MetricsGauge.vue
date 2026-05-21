<template>
	<VChart class="w-full" autoresize :option="chartOption" :style="{ height: `${height}px` }" />
</template>

<script setup lang="ts">
import type { GaugeSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { GaugeChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, toRefs } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"

const props = withDefaults(
	defineProps<{
		value: number
		title?: string
		height?: number
	}>(),
	{
		title: "CPU Idle",
		height: 220
	}
)

use([CanvasRenderer, GaugeChart, TooltipComponent, GridComponent])

type ChartOption = ComposeOption<TooltipComponentOption | GridComponentOption | GaugeSeriesOption>

const { value, title, height } = toRefs(props)
const style = computed(() => useThemeStore().style)

const chartOption = computed((): ChartOption => ({
	backgroundColor: "transparent",
	series: [
		{
			type: "gauge",
			startAngle: 220,
			endAngle: -40,
			min: 0,
			max: 100,
			detail: {
				formatter: "{value}%",
				fontSize: 18,
				color: style.value["fg-default-color"],
				offsetCenter: [0, "70%"]
			},
			data: [{ value: Math.round(value.value * 10) / 10, name: title.value }],
			axisLine: {
				lineStyle: {
					width: 15,
					color: [
						[0.2, "#ef4444"],
						[0.5, "#eab308"],
						[1, "#22c55e"]
					]
				}
			},
			pointer: { length: "60%", width: 4, itemStyle: { color: style.value["primary-color"] } },
			axisTick: { show: false },
			splitLine: { length: 10, lineStyle: { color: style.value["border-color"] } },
			axisLabel: { color: style.value["fg-secondary-color"], fontSize: 10 },
			title: {
				color: style.value["fg-secondary-color"],
				fontSize: 12,
				offsetCenter: [0, "90%"]
			}
		}
	]
}))
</script>
