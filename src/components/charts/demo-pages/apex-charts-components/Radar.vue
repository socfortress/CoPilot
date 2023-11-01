<template>
	<CardCodeExample title="Radar" class="!grid card">
		<Apex type="radar" width="100%" :options="chartOptions" :series="series"></Apex>
	</CardCodeExample>
</template>

<script setup lang="ts">
import Apex from "@/components/charts/Apex.vue"
import { ref, computed, watch } from "vue"
import { useThemeStore } from "@/stores/theme"

const style: { [key: string]: any } = computed(() => useThemeStore().style)
const isThemeDark = computed(() => useThemeStore().isThemeDark)

const series = ref([
	{
		name: "Series 1",
		data: [20, 100, 40, 30, 50, 80, 33]
	}
])

function getOptions() {
	return {
		chart: {
			width: "100%",
			type: "radar",
			toolbar: {
				show: false
			}
		},
		dataLabels: {
			enabled: true
		},
		plotOptions: {
			radar: {
				//size: 140,
				polygons: {
					strokeColors: style.value["--bg-color"],
					fill: {
						colors: [style.value["--bg-body"], style.value["--bg-color"]]
					}
				}
			}
		},
		colors: [style.value["--primary-color"]],
		markers: {
			size: 4,
			colors: ["#fff"],
			strokeColor: style.value["--primary-color"],
			strokeWidth: 2
		},
		tooltip: {
			y: {
				formatter: function (val: number) {
					return val
				}
			},
			theme: isThemeDark.value ? "dark" : "light"
		},
		xaxis: {
			categories: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
			labels: {
				style: {
					colors: [style.value["--fg-color"]]
				}
			}
		},
		yaxis: {
			tickAmount: 7,
			labels: {
				style: {
					colors: [style.value["--fg-color"]]
				},
				formatter: function (val: number, i: number) {
					if (i % 2 === 0) {
						return val
					} else {
						return ""
					}
				}
			}
		}
	}
}

const chartOptions = ref(getOptions())

watch(style, () => {
	chartOptions.value = getOptions()
})
</script>

<style scoped lang="scss">
.card {
	height: 100%;
	:deep(.n-card-header) {
		height: 68px;
	}

	:deep() {
		.apexcharts-text {
			fill: var(--fg-secondary-color);
		}
	}
}
</style>
