<template>
	<section class="flex flex-col gap-4">
		<h3 class="text-primary text-lg font-semibold">Metrics Summary</h3>
		<div class="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
			<MetricsStatCard label="Uptime" :value="summary.uptime" format="uptime" />
			<MetricsStatCard label="Total Memory" :value="summary.total_mem" format="bytes" />
			<MetricsStatCard label="CPUs" :value="summary.cpus" />
			<MetricsStatCard label="Processes" :value="summary.total_processes" />
			<MetricsStatCard
				label="CPU Idle"
				:value="summary.cpu_idle"
				format="percent"
				:decimals="1"
				:color-thresholds="{ low: 20, mid: 50 }"
			/>
			<MetricsStatCard label="Swap Free" :value="summary.swap_free" format="bytes" />
			<MetricsStatCard label="Users Logged In" :value="summary.logged_on_users" />
		</div>
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
			<n-card>
				<MetricsGauge :value="cpuIdle" title="CPU Idle" :height="220" />
			</n-card>
			<n-card class="lg:col-span-2">
				<MetricsChart title="System Load" :series="loadSeries" :height="220" />
			</n-card>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { MetricsSummaryData, TimeSeriesData } from "@/types/metrics.d"
import { NCard } from "naive-ui"
import { computed } from "vue"
import MetricsChart from "../MetricsChart.vue"
import MetricsGauge from "../MetricsGauge.vue"
import MetricsStatCard from "../MetricsStatCard.vue"

const { summary } = defineProps<{
	summary: MetricsSummaryData
}>()

const EMPTY_SERIES: TimeSeriesData = {}

const cpuIdle = computed(() => summary.cpu_idle ?? 0)
const loadSeries = computed(() => summary.load ?? EMPTY_SERIES)
</script>
