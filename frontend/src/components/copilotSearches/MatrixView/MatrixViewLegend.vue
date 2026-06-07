<template>
	<div class="bg-secondary border-default flex flex-wrap items-center gap-2.5 rounded-lg border px-2.5 py-1.5">
		<span class="text-tertiary text-xs">Rules:</span>
		<div v-for="step of legendSteps" :key="step.label" class="inline-flex items-center gap-1.5">
			<span class="border-default inline-block size-3.5 rounded border" :class="step.cls" />
			<span class="text-secondary text-xs">{{ step.label }}</span>
		</div>
		<div v-if="coverage" class="text-secondary ml-auto text-xs">
			<strong>{{ coverage.stats.covered_techniques }}</strong>
			/
			<strong>{{ coverage.stats.total_techniques }}</strong>
			techniques ·
			<strong>{{ coverage.stats.total_rules }}</strong>
			rules
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MitreCoverageResponse } from "@/types/copilotSearches.d"

defineProps<{
	coverage: MitreCoverageResponse | null
}>()

const legendSteps = [
	{ label: "0", cls: "cov-empty" },
	{ label: "1", cls: "cov-1" },
	{ label: "2-3", cls: "cov-2" },
	{ label: "4-7", cls: "cov-3" },
	{ label: "8+", cls: "cov-4" }
] as const
</script>
