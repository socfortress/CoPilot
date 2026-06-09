<template>
	<section class="flex flex-col gap-4">
		<h3 class="text-primary text-lg font-semibold">Memory</h3>
		<div class="mb-4 grid grid-cols-2 gap-4">
			<MetricsStatCard label="Swap Total" :value="memory.swap_total" format="bytes" />
			<MetricsStatCard label="Swap Free" :value="memory.swap_free" format="bytes" />
		</div>
		<n-card>
			<MetricsChart
				title="Memory Usage"
				:series="memory.mem_used || {}"
				:height="280"
				y-axis-name="bytes"
				use-format-bytes
			/>
		</n-card>
	</section>
</template>

<script setup lang="ts">
import type { MetricsMemoryData } from "@/types/metrics.d"
import { NCard } from "naive-ui"
import MetricsChart from "../MetricsChart.vue"
import MetricsStatCard from "../MetricsStatCard.vue"

defineProps<{
	memory: MetricsMemoryData
}>()
</script>
