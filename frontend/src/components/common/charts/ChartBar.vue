<template>
	<div ref="containerRef" class="chart-root" :style="{ height, width: '100%' }" />
</template>

<script setup lang="ts">
import type { ECharts } from "echarts/core"
import { init as echartsInit } from "echarts/core"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useThemeStore } from "@/stores/theme"
import { DASHBOARD_CHART_COLORS } from "./chartColors"
import "./echartsRegister"

const props = withDefaults(
	defineProps<{
		labels?: string[]
		data?: number[]
		height?: string
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

const containerRef = ref<HTMLElement | null>(null)
const themeStore = useThemeStore()
let chart: ECharts | null = null
let resizeObserver: ResizeObserver | null = null

function buildOption() {
	const style = themeStore.style
	const fg = style["fg-default-color"]

	return {
		tooltip: {
			trigger: "axis",
			axisPointer: { type: "shadow" }
		},
		grid: { left: 10, right: 30, top: 10, bottom: 10, containLabel: true },
		xAxis: {
			type: "value",
			axisLabel: { color: fg, fontSize: 10 },
			splitLine: { lineStyle: { color: `${fg}1a` } }
		},
		yAxis: {
			type: "category",
			data: [...props.labels].reverse(),
			axisLabel: {
				color: fg,
				fontSize: 10,
				width: 180,
				overflow: "truncate"
			},
			axisLine: { lineStyle: { color: `${fg}33` } }
		},
		series: [
			{
				type: "bar",
				data: [...props.data].reverse(),
				color: DASHBOARD_CHART_COLORS,
				itemStyle: { borderRadius: [0, 2, 2, 0] }
			}
		]
	}
}

function render() {
	if (!chart || !containerRef.value) return
	chart.setOption(buildOption(), true)
}

onMounted(() => {
	if (!containerRef.value) return
	chart = echartsInit(containerRef.value)
	chart.on("click", (params: { name?: string }) => {
		if (params.name) emit("itemClick", { name: params.name })
	})
	render()
	resizeObserver = new ResizeObserver(() => chart?.resize())
	resizeObserver.observe(containerRef.value)
})

watch(
	() => [props.labels, props.data, themeStore.style] as const,
	() => render(),
	{ deep: true }
)

onBeforeUnmount(() => {
	resizeObserver?.disconnect()
	resizeObserver = null
	chart?.dispose()
	chart = null
})
</script>
