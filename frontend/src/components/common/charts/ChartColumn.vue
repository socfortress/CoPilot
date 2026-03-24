<template>
	<div :style="{ height, width: '100%' }">
		<apexchart width="100%" :height :options="chartOptions" :series="chartSeries" />
	</div>
</template>

<script setup lang="ts">
import type { ApexOptions } from "apexcharts"
import { computed } from "vue"
import apexchart from "vue3-apexcharts"
import { useSettingsStore } from "@/stores/settings"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
import { DASHBOARD_CHART_COLORS } from "./chartColors"
import "@/assets/scss/overrides/apexchart-override.scss"

const props = withDefaults(
	defineProps<{
		labels?: string[]
		data?: number[]
		height?: string
		monochrome?: boolean
		labelsDatetime?: boolean
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
const dFormats = useSettingsStore().dateFormat

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
		responsive: [
			{
				breakpoint: 1200,
				options: {
					xaxis: {
						labels: {
							show: false
						}
					}
				}
			}
		],
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
				horizontal: false,
				distributed: true,
				borderRadius: 4,
				borderRadiusApplication: "end",
				columnWidth: "60%"
			}
		},
		dataLabels: { enabled: false },
		stroke: { show: false },
		xaxis: {
			categories: Array.from(props.labels, label => {
				return props.labelsDatetime
					? [dayjs(label).format(dFormats.date), dayjs(label).format(dFormats.time)]
					: label
			}),
			labels: {
				style: { colors: fg, fontSize: "9px" },
				rotate: -65,
				rotateAlways: true,
				hideOverlappingLabels: true,
				trim: false
			},
			axisBorder: { show: false },
			axisTicks: { show: false }
		},
		yaxis: {
			labels: {
				style: { colors: fg, fontSize: "10px" }
			}
		},
		grid: {
			borderColor: bc,
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
				fontFamily: ff
			}
		}
	}
})
</script>
