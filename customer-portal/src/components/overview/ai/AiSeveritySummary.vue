<template>
	<div class="flex flex-col gap-4 p-5">
		<div class="flex items-baseline gap-2">
			<span class="font-mono text-3xl leading-none font-semibold tracking-tight tabular-nums">
				{{ attention }}
			</span>
			<span class="text-secondary text-sm">high or critical</span>
		</div>

		<StatusBar :segments />
		<StatusLegend :segments variant="stacked" />
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import StatusBar from "../shared/StatusBar.vue"
import StatusLegend from "../shared/StatusLegend.vue"
import { attentionCount, severitySegments } from "./severity"

const { severityCounts } = defineProps<{
	/** Latest-report severity per analyzed alert, as returned by the insights endpoint. */
	severityCounts: Record<string, number>
}>()

const segments = computed(() => severitySegments(severityCounts))
const attention = computed(() => attentionCount(segments.value))
</script>
