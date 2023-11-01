<template>
	<CardCodeExample title="Sync">
		<div class="flex flex-col">
			<Apex type="line" height="160" :options="chartOptionsLine1" :series="seriesLine1"></Apex>
			<Apex type="line" height="160" :options="chartOptionsLine2" :series="seriesLine2"></Apex>
			<Apex type="area" height="160" :options="chartOptionsArea1" :series="seriesArea1"></Apex>
			<div class="grid sm:grid-cols-2 grid-cols-1">
				<div class="overflow-hidden">
					<Apex
						@mounted="chart1 = $event"
						type="area"
						height="160"
						:options="chartOptionsSmall1"
						:series="seriesSmall1"
					></Apex>
				</div>
				<div class="overflow-hidden">
					<Apex
						@mounted="chart2 = $event"
						type="area"
						height="160"
						:options="chartOptionsSmall2"
						:series="seriesSmall2"
					></Apex>
				</div>
			</div>
		</div>
	</CardCodeExample>
</template>

<script setup lang="ts">
import "@/assets/scss/apexchart-override.scss"
import { computed, ref, watch } from "vue"
import { generateDayWiseTimeSeries } from "./utils"
import _merge from "lodash/merge"
import _clone from "lodash/cloneDeep"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
import Apex, { type VueApexChartsComponent } from "@/components/charts/Apex.vue"
import { useResizeObserver } from "@vueuse/core"

const isThemeDark = computed(() => useThemeStore().isThemeDark)
const style: { [key: string]: any } = computed(() => useThemeStore().style)
const startDate = dayjs().subtract(20, "d").valueOf()

const card = ref(null)
const chart1 = ref<VueApexChartsComponent | null>(null)
const chart2 = ref<VueApexChartsComponent | null>(null)

function getCommonOptions() {
	return {
		chart: {
			height: 160,
			toolbar: {
				show: false
			}
		},
		colors: [],
		dataLabels: {
			enabled: false
		},
		stroke: {
			curve: "straight"
		},
		toolbar: {
			tools: {
				selection: false
			}
		},
		markers: {
			size: 4,
			hover: {
				size: 10
			}
		},
		tooltip: {
			followCursor: false,
			theme: isThemeDark.value ? "dark" : "light",
			x: {
				show: false
			},
			marker: {
				show: false
			},
			y: {
				title: {
					formatter: function () {
						return ""
					}
				}
			}
		},
		grid: {
			clipMarkers: false,
			borderColor: isThemeDark.value ? "#ffffff11" : "#00000011"
		},
		yaxis: {
			tickAmount: 2,
			labels: {
				show: true,
				align: "right",
				style: {
					colors: style.value["--fg-color"],
					fontSize: "10px",
					fontFamily: style.value["--font-family-mono"]
				}
			}
		},
		xaxis: {
			type: "datetime",
			labels: {
				show: true,
				align: "right",
				style: {
					colors: style.value["--fg-color"],
					fontSize: "10px",
					fontFamily: style.value["--font-family-mono"]
				}
			}
		}
	}
}

const seriesLine1 = ref([
	{
		data: generateDayWiseTimeSeries(startDate, 20, {
			min: 10,
			max: 60
		})
	}
])
const seriesLine2 = ref([
	{
		data: generateDayWiseTimeSeries(startDate, 20, {
			min: 10,
			max: 30
		})
	}
])
const seriesArea1 = ref([
	{
		data: generateDayWiseTimeSeries(startDate, 20, {
			min: 10,
			max: 60
		})
	}
])
const seriesSmall1 = ref([
	{
		data: generateDayWiseTimeSeries(startDate, 20, {
			min: 10,
			max: 60
		})
	}
])
const seriesSmall2 = ref([
	{
		data: generateDayWiseTimeSeries(startDate, 20, {
			min: 10,
			max: 60
		})
	}
])

function getChartOptionsLine1() {
	return _merge(_clone(getCommonOptions()), {
		chart: {
			id: "fb",
			group: "social",
			type: "line",
			height: 160,
			toolbar: {
				show: true
			}
		},
		colors: [style.value["--primary-color"]]
	})
}
function getChartOptionsLine2() {
	return _merge(_clone(getCommonOptions()), {
		chart: {
			id: "tw",
			group: "social",
			type: "line",
			height: 160
		},
		colors: [style.value["--secondary1-color"]]
	})
}
function getChartOptionsArea1() {
	return _merge(_clone(getCommonOptions()), {
		chart: {
			id: "yt",
			group: "social",
			type: "area",
			height: 160
		},
		colors: [style.value["--secondary2-color"]]
	})
}
function getChartOptionsSmall1() {
	return _merge(_clone(getCommonOptions()), {
		chart: {
			id: "ig",
			group: "social",
			type: "area",
			height: 160
		},
		colors: [style.value["--secondary3-color"]]
	})
}
function getChartOptionsSmall2() {
	return _merge(_clone(getCommonOptions()), {
		chart: {
			id: "li",
			group: "social",
			type: "area",
			height: 160
		},
		colors: [style.value["--secondary4-color"]]
	})
}

const chartOptionsLine1 = ref(getChartOptionsLine1())
const chartOptionsLine2 = ref(getChartOptionsLine2())
const chartOptionsArea1 = ref(getChartOptionsArea1())
const chartOptionsSmall1 = ref(getChartOptionsSmall1())
const chartOptionsSmall2 = ref(getChartOptionsSmall2())

watch(isThemeDark, () => {
	chartOptionsLine1.value = getChartOptionsLine1()
	chartOptionsLine2.value = getChartOptionsLine2()
	chartOptionsArea1.value = getChartOptionsArea1()
	chartOptionsSmall1.value = getChartOptionsSmall1()
	chartOptionsSmall2.value = getChartOptionsSmall2()
})

useResizeObserver(card, () => {
	chart1.value?.refresh()
	chart2.value?.refresh()
})
</script>
