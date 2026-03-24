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

const chartSeries = computed<number[]>(() => {
	if (!props.labels.length) return []
	return props.labels.map((_, i) => Number(props.data[i] ?? 0))
})

const chartOptions = computed<ApexOptions>(() => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const ff = style["font-family"]

	return {
		chart: {
			type: "donut",
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
		labels: [...props.labels],
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
			pie: {
				expandOnClick: false,
				donut: {
					size: "55%",
					labels: {
						show: true,
						value: { color: fg }
					}
				}
			}
		},
		dataLabels: {
			enabled: true
		},
		stroke: {
			show: false
		},
		legend: {
			show: true,
			position: "right",
			fontSize: "11px",
			fontFamily: ff,
			labels: { colors: fg },
			itemMargin: { vertical: 6, horizontal: 4 },
			markers: {
				size: 7,
				strokeWidth: 0,
				offsetX: -5
			},
			formatter: (seriesName, opts) => {
				const series = opts.w.globals.series as number[]
				const value = series[opts.seriesIndex] ?? 0
				const total = series.reduce((sum, v) => sum + v, 0)
				const pct = total > 0 ? (value / total) * 100 : 0
				return `${seriesName} - ${value} (${pct.toFixed(1)}%)`
			}
		},
		tooltip: {
			theme: themeStore.isThemeDark ? "dark" : "light"
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
