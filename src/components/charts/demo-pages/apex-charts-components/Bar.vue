<template>
	<CardCodeExample title="Bar">
		<Apex type="bar" height="350" :options="chartOptions" :series="series"></Apex>
	</CardCodeExample>
</template>

<script setup lang="ts">
import "@/assets/scss/apexchart-override.scss"
import { computed, ref, watch } from "vue"
import Apex from "@/components/charts/Apex.vue"
import { useThemeStore } from "@/stores/theme"

const isThemeDark = computed(() => useThemeStore().isThemeDark)
const style: { [key: string]: any } = computed(() => useThemeStore().style)

const series = ref([
	{
		name: "Marine Sprite",
		data: [44, 55, 41, 37, 22, 43, 21]
	},
	{
		name: "Striking Calf",
		data: [53, 32, 33, 52, 13, 43, 32]
	},
	{
		name: "Tank Picture",
		data: [12, 17, 11, 9, 15, 11, 20]
	},
	{
		name: "Bucket Slope",
		data: [9, 7, 5, 8, 6, 9, 4]
	},
	{
		name: "Reborn Kid",
		data: [25, 12, 19, 32, 25, 24, 10]
	}
])

function getOptions() {
	return {
		chart: {
			type: "bar",
			height: 350,
			stacked: true
		},
		plotOptions: {
			bar: {
				horizontal: true,
				dataLabels: {
					total: {
						enabled: true,
						offsetX: 0,
						style: {
							fontSize: "13px",
							fontWeight: 900,
							fontFamily: style.value["--font-family-mono"],
							color: style.value["--fg-color"]
						}
					}
				}
			}
		},
		stroke: {
			width: 1,
			colors: [!isThemeDark.value ? "#ffffffaa" : "#000000aa"]
		},
		title: {
			text: "Fiction Books Sales",
			style: {
				color: style.value["--fg-color"],
				fontSize: "16px",
				fontFamily: style.value["--font-family"]
			}
		},
		grid: {
			borderColor: isThemeDark.value ? "#ffffff11" : "#00000011"
		},
		xaxis: {
			categories: [2017, 2018, 2019, 2020, 2021, 2022, 2023],
			labels: {
				formatter: function (val: number) {
					return val + "K"
				},
				style: {
					colors: style.value["--fg-color"],
					fontSize: "10px",
					fontFamily: style.value["--font-family-mono"]
				}
			}
		},
		yaxis: {
			theme: isThemeDark.value ? "dark" : "light",
			title: {
				text: undefined
			},
			labels: {
				style: {
					colors: style.value["--fg-color"],
					fontSize: "10px",
					fontFamily: style.value["--font-family-mono"]
				}
			}
		},
		tooltip: {
			y: {
				formatter: function (val: number) {
					return val + "K"
				}
			},
			theme: isThemeDark.value ? "dark" : "light"
		},
		fill: {
			opacity: 1
		},
		legend: {
			position: "top",
			horizontalAlign: "left",
			offsetX: 40,
			labels: {
				colors: style.value["--fg-color"]
			}
		}
	}
}

const chartOptions = ref(getOptions())

watch(isThemeDark, () => {
	chartOptions.value = getOptions()
})
</script>
