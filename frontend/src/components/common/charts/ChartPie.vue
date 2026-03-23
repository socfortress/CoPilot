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
	const pieData = props.labels.map((label, i) => ({
		value: props.data[i],
		name: label
	}))
	return {
		tooltip: {
			trigger: "item",
			formatter: "{b}: <strong>{c}</strong> ({d}%)"
		},
		legend: {
			type: "scroll",
			orient: "vertical",
			right: 10,
			top: 20,
			bottom: 20,
			textStyle: { color: style["fg-default-color"], fontSize: 11 }
		},
		series: [
			{
				type: "pie",
				radius: ["40%", "70%"],
				center: ["35%", "50%"],
				avoidLabelOverlap: true,
				itemStyle: {
					borderColor: style["bg-default-color"],
					borderWidth: 2,
					borderRadius: 4
				},
				label: { show: false },
				color: DASHBOARD_CHART_COLORS,
				data: pieData
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
