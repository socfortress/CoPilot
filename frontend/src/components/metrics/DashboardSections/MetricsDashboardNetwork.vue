<template>
	<section class="flex flex-col gap-4">
		<h3 class="text-primary text-lg font-semibold">Network</h3>
		<div class="mb-4">
			<MetricsStatCard label="TCP Sessions Established" :value="network.tcp_established" />
		</div>
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<n-card>
				<MetricsChart
					title="Network Traffic (bytes/s)"
					:series="trafficSeries"
					:height="280"
					y-axis-name="B/s"
					use-format-bytes
				/>
			</n-card>
			<n-card>
				<MetricsChart title="Interface Errors" :series="interfaceErrorsSeries" :height="280" />
			</n-card>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { MetricsNetworkData, TimeSeriesData } from "@/types/metrics.d"
import { NCard } from "naive-ui"
import { computed } from "vue"
import MetricsChart from "../MetricsChart.vue"
import MetricsStatCard from "../MetricsStatCard.vue"

const { network } = defineProps<{
	network: MetricsNetworkData
}>()

const EMPTY_SERIES: TimeSeriesData = {}

const trafficSeries = computed(() => network.traffic ?? EMPTY_SERIES)
const interfaceErrorsSeries = computed(() => network.interface_errors ?? EMPTY_SERIES)
</script>
