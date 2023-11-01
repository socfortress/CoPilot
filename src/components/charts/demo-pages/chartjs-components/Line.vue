<template>
	<CardCodeExample title="Line">
		<Line :data="data" :options="options" />
	</CardCodeExample>
</template>

<script setup lang="ts">
import {
	Chart as ChartJS,
	CategoryScale,
	LinearScale,
	PointElement,
	LineElement,
	Title,
	Tooltip,
	Legend
} from "chart.js"
import { Line } from "vue-chartjs"

import { computed, watch, ref } from "vue"

import { useThemeStore } from "@/stores/theme"

const style: { [key: string]: any } = computed(() => useThemeStore().style)

const data = {
	labels: ["January", "February", "March", "April", "May", "June", "July"],
	datasets: [
		{
			label: "Data One",
			backgroundColor: style.value["--primary-color"],
			borderColor: style.value["--primary-color"],
			data: [40, 39, 10, 40, 39, 80, 40]
		}
	]
}

function getOptions() {
	return {
		responsive: true,
		maintainAspectRatio: false,
		color: style.value["--fg-color"],
		scales: {
			y: {
				ticks: { color: style.value["--fg-secondary-color"] }
			},
			x: {
				ticks: { color: style.value["--fg-secondary-color"] }
			}
		}
	}
}

const options = ref(getOptions())

watch(style, () => {
	options.value = getOptions()
})

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)
</script>
