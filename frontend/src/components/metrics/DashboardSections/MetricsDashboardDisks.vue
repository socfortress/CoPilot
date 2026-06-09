<template>
	<section class="flex flex-col gap-4">
		<h3 class="text-primary text-lg font-semibold">Disks</h3>
		<div class="mb-4">
			<MetricsStatCard label="Total Disk Size" :value="disks.disk_total" format="bytes" />
		</div>
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<n-card>
				<MetricsChart title="Disk Usage %" :series="diskUsageSeries" y-axis-name="%" />
			</n-card>
			<n-card>
				<MetricsChart title="Disk I/O (bytes/s)" :series="diskIoSeries" y-axis-name="B/s" use-format-bytes />
			</n-card>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { MetricsDisksData, TimeSeriesData } from "@/types/metrics.d"
import { NCard } from "naive-ui"
import { computed } from "vue"
import MetricsChart from "../MetricsChart.vue"
import MetricsStatCard from "../MetricsStatCard.vue"

const { disks } = defineProps<{
	disks: MetricsDisksData
}>()

const EMPTY_SERIES: TimeSeriesData = {}

const diskUsageSeries = computed(() => disks.disk_usage ?? EMPTY_SERIES)
const diskIoSeries = computed(() => disks.disk_io ?? EMPTY_SERIES)
</script>
