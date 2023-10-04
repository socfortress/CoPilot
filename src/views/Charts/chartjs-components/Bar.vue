<template>
	<CardCodeExample title="Bar">
		<Bar :data="data" :options="options" />
	</CardCodeExample>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from "chart.js"
import { Bar } from "vue-chartjs"
import { computed, watch, ref } from "vue"
const style: { [key: string]: any } = computed(() => useThemeStore().style)

const data = {
	labels: [
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December"
	],
	datasets: [
		{
			label: "Data One",
			backgroundColor: style.value["--primary-color"],
			data: [40, 20, 12, 39, 10, 40, 39, 80, 40, 20, 12, 11]
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

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)
</script>
