<template>
	<section class="flex flex-col gap-4">
		<h3 class="text-primary text-lg font-semibold">Processes</h3>
		<div class="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
			<MetricsStatCard label="Running" :value="processes.running" />
			<MetricsStatCard label="Sleeping" :value="processes.sleeping" />
			<MetricsStatCard label="Unknown" :value="processes.unknown" />
			<MetricsStatCard label="Zombies" :value="processes.zombies" />
		</div>
		<n-card>
			<MetricsChart title="Process Status" :series="statusSeries" :height="280" />
		</n-card>
	</section>
</template>

<script setup lang="ts">
import type { MetricsProcessesData, TimeSeriesData } from "@/types/metrics.d"
import { NCard } from "naive-ui"
import { computed } from "vue"
import MetricsChart from "../MetricsChart.vue"
import MetricsStatCard from "../MetricsStatCard.vue"

const { processes } = defineProps<{
	processes: MetricsProcessesData
}>()

const EMPTY_SERIES: TimeSeriesData = {}

const statusSeries = computed(() => processes.status ?? EMPTY_SERIES)
</script>
