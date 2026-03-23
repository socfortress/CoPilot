<template>
	<div :style="{ height, width: '100%' }">
		<apexchart width="100%" :height :options="chartOptions" :series="chartSeries" />
	</div>
</template>

<script setup lang="ts">
import type { ApexOptions } from "apexcharts"
import { computed } from "vue"
import apexchart from "vue3-apexcharts"
import { useThemeStore } from "@/stores/theme"
import { DASHBOARD_CHART_COLORS } from "./chartColors"
import "@/assets/scss/overrides/apexchart-override.scss"

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

const themeStore = useThemeStore()

const chartSeries = computed<number[]>(() => {
	if (!props.labels.length) return []
	return props.labels.map((_, i) => Number(props.data[i] ?? 0))
})

const chartOptions = computed<ApexOptions>(() => {
	const style = themeStore.style
	const bg = style["bg-default-color"]
	const fg = style["fg-default-color"]

	return {
		chart: {
			type: "donut",
			fontFamily: style["font-family"],
			toolbar: { show: false },
			animations: { enabled: true },
			events: {
				dataPointSelection(_event, _chartContext, config) {
					const idx = config.dataPointIndex
					const name = props.labels[idx]
					if (name) emit("itemClick", { name })
				}
			}
		},
		labels: [...props.labels],
		colors: DASHBOARD_CHART_COLORS,
		plotOptions: {
			pie: {
				donut: {
					size: "55%",
					labels: { show: false }
				},
				expandOnClick: false
			}
		},
		dataLabels: { enabled: false },
		stroke: {
			width: 2,
			colors: [bg]
		},
		legend: {
			show: true,
			position: "right",
			fontSize: "11px",
			fontFamily: style["font-family"],
			labels: { colors: fg },
			itemMargin: { vertical: 4 }
		},
		tooltip: {
			theme: themeStore.isThemeDark ? "dark" : "light",
			y: {
				formatter: (val: number) => String(val)
			}
		},
		noData: {
			text: "No data",
			align: "center",
			style: {
				color: fg,
				fontSize: "16px",
				fontFamily: style["font-family"]
			}
		}
	}
})
</script>
