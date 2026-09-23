<template>
	<div class="flex flex-col gap-4 p-5">
		<div class="flex items-baseline gap-2">
			<span class="ai-summary__headline">{{ attention }}</span>
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

<style lang="scss" scoped>
.ai-summary__headline {
	font-family: var(--font-family-mono);
	font-size: 1.75rem;
	font-weight: 600;
	line-height: 1;
	letter-spacing: -0.03em;
	font-variant-numeric: tabular-nums;
}
</style>
