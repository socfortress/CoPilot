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
	const rotate = props.labels.length > 20 ? -45 : 0

	return {
		chart: {
			type: "bar",
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
		colors: props.monochrome ? [DASHBOARD_CHART_COLORS[0]] : DASHBOARD_CHART_COLORS,
		plotOptions: {
			bar: {
				horizontal: false,
				distributed: true,
				borderRadius: 2,
				borderRadiusApplication: "end",
				columnWidth: "60%"
			}
		},
		dataLabels: { enabled: false },
		stroke: { show: false },
		xaxis: {
			categories: [...props.labels],
			labels: {
				style: { colors: fg, fontSize: "10px" },
				rotate,
				rotateAlways: rotate !== 0,
				hideOverlappingLabels: true,
				trim: true
			},
			axisBorder: { color: `${fg}33` },
			axisTicks: { show: false }
		},
		yaxis: {
			labels: {
				style: { colors: fg, fontSize: "10px" }
			}
		},
		grid: {
			borderColor: `${fg}1a`,
			strokeDashArray: 0,
			xaxis: { lines: { show: false } },
			yaxis: { lines: { show: true } }
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
				fontFamily: style["font-family"]
			}
		}
	}
})
</script>
