<template>
	<section class="flex flex-col gap-4">
		<h3 class="text-primary text-lg font-semibold">Kernel</h3>
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<n-card>
				<MetricsChart title="Interrupts/sec" :series="interruptsSeries" y-axis-name="/s" />
			</n-card>
			<n-card>
				<MetricsChart title="Processes Forked/sec" :series="processesForkedSeries" y-axis-name="/s" />
			</n-card>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { MetricsKernelData, TimeSeriesData } from "@/types/metrics.d"
import { NCard } from "naive-ui"
import { computed } from "vue"
import MetricsChart from "../MetricsChart.vue"

const { kernel } = defineProps<{
	kernel: MetricsKernelData
}>()

const EMPTY_SERIES: TimeSeriesData = {}

const interruptsSeries = computed(() => kernel.interrupts ?? EMPTY_SERIES)
const processesForkedSeries = computed(() => kernel.processes_forked ?? EMPTY_SERIES)
</script>
