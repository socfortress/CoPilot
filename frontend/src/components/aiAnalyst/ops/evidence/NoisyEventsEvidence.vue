<template>
	<div v-if="view" class="flex flex-col gap-3" data-testid="talon-ops-evidence-noisy-events">
		<div class="flex flex-col gap-1">
			<div class="flex items-baseline justify-between gap-2 text-sm">
				<span>Share of the pattern's events</span>
				<span class="font-mono tabular-nums" data-testid="talon-ops-evidence-share">{{ pctText(Math.round(view.share * 10) / 10) }}</span>
			</div>
			<n-progress
				type="line"
				:percentage="view.share"
				:show-indicator="false"
				:height="8"
				:aria-label="`${pctText(Math.round(view.share * 10) / 10)} of the pattern's events`"
			/>
		</div>
		<EvidenceBars :groups="view.groups" />
		<EvidenceFigures :items="view.figures" />
	</div>
</template>

<script setup lang="ts">
// `noisy_events`: one candidate's share of its pattern's events, and its estimated GB per day against
// the floor it passed and the customer's measured volume.
import type { Evidence } from "./evidence"
import { NProgress } from "naive-ui"
import { computed } from "vue"
import { noisyEventsView, pctText } from "./evidence"
import EvidenceBars from "./EvidenceBars.vue"
import EvidenceFigures from "./EvidenceFigures.vue"

const { evidence } = defineProps<{ evidence: Evidence | null }>()
const view = computed(() => noisyEventsView(evidence))
</script>
