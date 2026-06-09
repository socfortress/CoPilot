<template>
	<section class="flex flex-col gap-4">
		<h3 class="text-primary text-lg font-semibold">CPU</h3>
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<n-card>
				<MetricsChart title="CPU System %" :series="cpu.cpu_usage_system || {}" y-axis-name="%" />
			</n-card>
			<n-card>
				<MetricsChart title="CPU User %" :series="cpu.cpu_usage_user || {}" y-axis-name="%" />
			</n-card>
			<n-card>
				<MetricsChart title="I/O Wait %" :series="cpu.cpu_iowait || {}" y-axis-name="%" />
			</n-card>
			<n-card>
				<MetricsChart title="Soft IRQ %" :series="cpu.cpu_softirq || {}" y-axis-name="%" />
			</n-card>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { MetricsCpuData } from "@/types/metrics.d"
import { NCard } from "naive-ui"
import MetricsChart from "../MetricsChart.vue"

defineProps<{
	cpu: MetricsCpuData
}>()
</script>
