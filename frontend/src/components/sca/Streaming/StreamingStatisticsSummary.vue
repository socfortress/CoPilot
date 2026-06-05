<template>
	<n-card v-if="stats" class="mb-4">
		<div class="flex flex-wrap justify-between gap-4">
			<n-statistic label="Total Agents" :value="stats.total_agents" />
			<n-statistic label="Total Policies" :value="stats.total_policies" />
			<n-statistic label="Average Score">
				<template #default>
					<span :class="scoreClass(stats.average_score)">{{ stats.average_score }}%</span>
				</template>
			</n-statistic>
			<n-statistic label="Checks" :value="stats.total_checks" />
			<n-statistic label="Passed" :value="stats.total_passes" class="text-success" />
			<n-statistic label="Failed" :value="stats.total_fails" class="text-error" />
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { ScaStreamComplete } from "@/types/sca.d"
import { NCard, NStatistic } from "naive-ui"

defineProps<{
	stats: ScaStreamComplete
}>()

function scoreClass(score: number): string {
	if (score >= 80) return "text-success"
	if (score >= 60) return "text-warning"
	return "text-error"
}
</script>
