<template>
	<!--
		The failures by severity as a labelled bar list: each row names its severity and prints its
		count, so neither colour nor length is all that carries it. Bars scale to the largest count.
	-->
	<div class="flex flex-col gap-2" data-testid="cloud-severity-bars">
		<p v-if="!rows.length" class="text-secondary m-0 text-sm">No failing findings.</p>
		<div
			v-for="row of rows"
			:key="row.severity"
			class="grid grid-cols-[6.5rem_minmax(0,1fr)_3.5rem] items-center gap-3"
			:title="`${SEVERITY_LABELS[row.severity]}: ${row.count} failing (${Math.round(row.percent)}% of the failures)`"
			:data-testid="`cloud-severity-${row.severity}`"
		>
			<span class="text-secondary text-sm">{{ SEVERITY_LABELS[row.severity] }}</span>
			<span class="bg-secondary h-1.5 overflow-hidden rounded-full">
				<span class="block h-full rounded-full" :class="SEVERITY_FILLS[row.severity]" :style="{ width: `${row.width}%` }" />
			</span>
			<span class="text-default text-right font-mono text-sm tabular-nums">{{ row.count }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CloudScanCounts } from "@/types/cloud-assessment"
import { computed } from "vue"
import { SEVERITY_FILLS, SEVERITY_LABELS, severitySegments } from "./utils"

const { counts } = defineProps<{ counts: CloudScanCounts }>()

const rows = computed(() => {
	const segments = severitySegments(counts)
	const largest = Math.max(1, ...segments.map(segment => segment.count))
	// At least a sliver, so a count of 1 beside hundreds still shows a mark.
	return segments.map(segment => ({ ...segment, width: Math.max(2, (segment.count / largest) * 100) }))
})
</script>
