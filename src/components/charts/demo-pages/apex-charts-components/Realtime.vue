<template>
	<CardCodeExample title="Realtime">
		<Apex type="line" height="350" :options="chartOptions" :series="series" @mounted="chart = $event"></Apex>
	</CardCodeExample>
</template>

<script setup lang="ts">
import { useThemeStore } from "@/stores/theme"
import { computed, onMounted, ref, watch, onBeforeUnmount } from "vue"
import Apex, { type VueApexChartsComponent } from "@/components/charts/Apex.vue"

const chart = ref<VueApexChartsComponent | null>(null)
const isThemeDark = computed(() => useThemeStore().isThemeDark)
const style: { [key: string]: any } = computed(() => useThemeStore().style)

let lastDate = 0
let data: any[] = []
const TICKINTERVAL = 86400000
let XAXISRANGE = 777600000

function getDayWiseTimeSeries(
	baseval: number,
	count: number,
	yrange: {
		min: number
		max: number
	}
) {
	let i = 0
	while (i < count) {
		const x = baseval
		const y = Math.floor(Math.random() * (yrange.max - yrange.min + 1)) + yrange.min

		data.push({
			x,
			y
		})
		lastDate = baseval
		baseval += TICKINTERVAL
		i++
	}
}

getDayWiseTimeSeries(new Date("11 Feb 2017 GMT").getTime(), 10, {
	min: 10,
	max: 90
})

function getNewSeries(
	baseval: number,
	yrange: {
		min: number
		max: number
	}
) {
	var newDate = baseval + TICKINTERVAL
	lastDate = newDate

	for (var i = 0; i < data.length - 10; i++) {
		// IMPORTANT
		// we reset the x and y of the data which is out of drawing area
		// to prevent memory leaks
		data[i].x = newDate - XAXISRANGE - TICKINTERVAL
		data[i].y = 0
	}

	data.push({
		x: newDate,
		y: Math.floor(Math.random() * (yrange.max - yrange.min + 1)) + yrange.min
	})
}

function resetData() {
	// Alternatively, you can also reset the data at certain intervals to prevent creating a huge series
	data = data.slice(data.length - 10, data.length)
}

const series = ref([
	{
		data: data.slice()
	}
])
function getOptions() {
	return {
		chart: {
			id: "realtime",
			height: 350,
			type: "line",
			animations: {
				enabled: true,
				easing: "linear",
				dynamicAnimation: {
					speed: 1000
				}
			},
			toolbar: {
				show: false
			},
			zoom: {
				enabled: false
			}
		},
		dataLabels: {
			enabled: false
		},
		fill: {
			type: "gradient",
			gradient: {
				shade: "dark",
				gradientToColors: [style.value["--fg-color"]],
				shadeIntensity: 1,
				type: "horizontal",
				opacityFrom: 1,
				opacityTo: 1,
				stops: [0, 100, 100, 100]
			}
		},
		stroke: {
			curve: "smooth"
		},
		grid: {
			borderColor: isThemeDark.value ? "#ffffff11" : "#00000011"
		},
		title: {
			text: "Dynamic Updating Chart",
			align: "left",
			style: {
				color: style.value["--fg-color"],
				fontSize: "16px",
				fontFamily: style.value["--font-family"]
			}
		},
		markers: {
			size: 0
		},
		tooltip: {
			theme: isThemeDark.value ? "dark" : "light"
		},
		xaxis: {
			type: "datetime",
			range: XAXISRANGE,
			labels: {
				style: {
					colors: style.value["--fg-color"],
					fontSize: "10px",
					fontFamily: style.value["--font-family-mono"]
				}
			}
		},
		yaxis: {
			max: 100,
			labels: {
				style: {
					colors: style.value["--fg-color"],
					fontSize: "10px",
					fontFamily: style.value["--font-family-mono"]
				}
			}
		},
		legend: {
			show: false
		}
	}
}

const chartOptions = ref(getOptions())
let updateTimer = null as NodeJS.Timeout | null
let resetTimer = null as NodeJS.Timeout | null

onMounted(() => {
	updateTimer = setInterval(() => {
		getNewSeries(lastDate, {
			min: 10,
			max: 90
		})

		chart.value?.updateSeries([
			{
				data: data
			}
		])
	}, 1000)

	// every 60 seconds, we reset the data to prevent memory leaks
	resetTimer = setInterval(() => {
		resetData()

		chart.value?.updateSeries(
			[
				{
					data
				}
			],
			true
		)
	}, 60000)
})

onBeforeUnmount(() => {
	if (updateTimer) clearInterval(updateTimer)
	if (resetTimer) clearInterval(resetTimer)
})

watch(isThemeDark, () => {
	chartOptions.value = getOptions()
})
</script>
