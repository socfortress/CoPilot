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

const themeStore = useThemeStore()

const chartSeries = computed(() => [
	{
		name: "value",
		data: props.labels.map((_, i) => Number(props.data[i] ?? 0))
	}
])

const chartOptions = computed<ApexOptions>(() => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const bc = style["border-color"]
	const ff = style["font-family"]

	return {
		chart: {
			type: "bar",
			fontFamily: ff,
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
		colors: props.monochrome ? [DASHBOARD_CHART_COLORS[0]] : DASHBOARD_CHART_COLORS,
		states: {
			active: {
				allowMultipleDataPointsSelection: false,
				filter: {
					type: "none"
				}
			}
		},
		plotOptions: {
			bar: {
				expandOnClick: false,
				horizontal: true,
				distributed: true,
				borderRadius: 4,
				barHeight: "60%",
				dataLabels: {
					position: "top"
				}
			}
		},
		dataLabels: {
			enabled: true,
			textAnchor: "start",
			offsetX: 5,
			style: {
				fontSize: "12px",
				colors: ["#fff"]
			}
		},
		stroke: { show: false },
		xaxis: {
			categories: [...props.labels],
			labels: {
				style: { colors: fg, fontSize: "10px" }
			},
			axisBorder: { show: false },
			axisTicks: { show: false }
		},
		yaxis: {
			labels: {
				style: { colors: fg, fontSize: "11px" },
				maxWidth: 200,
				trim: true
			}
		},
		grid: {
			borderColor: bc,
			strokeDashArray: 0,
			xaxis: { lines: { show: true } },
			yaxis: { lines: { show: false } }
		},
		legend: { show: false },
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
				fontFamily: ff
			}
		}
	}
})
</script>
