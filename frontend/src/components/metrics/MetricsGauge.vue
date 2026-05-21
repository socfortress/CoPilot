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

/** Arco a gradiente come nell'esempio gauge-grade. */
const GRADE_AXIS_COLORS: [number, string][] = [
	[0.25, "#FF6E76"],
	[0.5, "#FDDD60"],
	[0.75, "#58D9F9"],
	[1, "#7CFFB2"]
]

const GAUGE_POINTER_ICON = "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z"

const { value, title, height } = toRefs(props)
const style = computed(() => useThemeStore().style)

const chartOption = computed((): ChartOption => {
	const fgSecondary = style.value["fg-secondary-color"]
	const gaugeValue = Math.min(1, Math.max(0, Math.round(value.value * 10) / 10 / 100))

	return {
		backgroundColor: "transparent",
		series: [
			{
				type: "gauge",
				startAngle: 180,
				endAngle: 0,
				center: ["50%", "75%"],
				radius: "90%",
				min: 0,
				max: 1,
				splitNumber: 8,
				axisLine: {
					lineStyle: {
						width: 6,
						color: GRADE_AXIS_COLORS
					}
				},
				pointer: {
					icon: GAUGE_POINTER_ICON,
					length: "12%",
					width: 20,
					offsetCenter: [0, "-60%"],
					itemStyle: { color: "auto" }
				},
				axisTick: {
					length: 12,
					lineStyle: { color: "auto", width: 2 }
				},
				splitLine: {
					length: 20,
					lineStyle: { color: "auto", width: 5 }
				},
				axisLabel: {
					color: fgSecondary,
					fontSize: 11,
					distance: -48,
					rotate: "tangential",
					formatter: (axisValue: number) => {
						if (axisValue === 0) return "0%"
						if (axisValue === 0.5) return "50%"
						if (axisValue === 1) return "100%"
						return ""
					}
				},
				title: {
					color: fgSecondary,
					fontSize: 13,
					offsetCenter: [0, "-10%"]
				},
				detail: {
					fontSize: 22,
					offsetCenter: [0, "-35%"],
					valueAnimation: true,
					formatter: (detailValue: number) => `${Math.round(detailValue * 100)}%`,
					color: "inherit"
				},
				data: [{ value: gaugeValue, name: title.value }]
			}
		]
	}
})
</script>
