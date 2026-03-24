<template>
	<div ref="gaugeEl" :style="{ height: `${height}px` }"></div>
</template>

<script setup lang="ts">
import type { ECharts } from "echarts/core"
import { GaugeChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { init as echartsInit, use as echartsUse } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, onBeforeUnmount, onMounted, ref, toRefs, watch } from "vue"
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

echartsUse([TooltipComponent, GridComponent, GaugeChart, CanvasRenderer])

const { value, title, height } = toRefs(props)

const gaugeEl = ref<HTMLElement | null>(null)
const chartCtx = ref<ECharts | null>(null)
const style = computed(() => useThemeStore().style)
let resizeObserver: ResizeObserver | null = null

function getOptions() {
	return {
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
	}
}

function renderChart() {
	if (!chartCtx.value) return
	chartCtx.value.setOption(getOptions(), true)
}

watch([value, style], renderChart)

onMounted(() => {
	if (!gaugeEl.value) return
	chartCtx.value = echartsInit(gaugeEl.value)
	renderChart()

	resizeObserver = new ResizeObserver(() => chartCtx.value?.resize())
	resizeObserver.observe(gaugeEl.value)
})

onBeforeUnmount(() => {
	resizeObserver?.disconnect()
	chartCtx.value?.dispose()
})
</script>
