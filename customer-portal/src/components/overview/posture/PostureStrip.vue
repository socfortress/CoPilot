<template>
	<section class="posture-strip bg-default border-default rounded-lg border" aria-label="Security posture">
		<PostureCell
			v-for="cell of cells"
			:key="cell.key"
			:cell
			:loading="loading[cell.key]"
			:error="errors[cell.key]"
			class="posture-strip__cell"
		/>
	</section>
</template>

<script setup lang="ts">
import type { PostureKey } from "./postureCells"
import type { AgentCounts, StatusCounts } from "@/composables/overview/useOverviewData"
import { computed } from "vue"
import PostureCell from "./PostureCell.vue"
import { buildPostureCells } from "./postureCells"

const { alertCounts, caseCounts, agentCounts } = defineProps<{
	alertCounts: StatusCounts
	caseCounts: StatusCounts
	agentCounts: AgentCounts
	/** Per cell: show the placeholder (first load only — refreshes keep the numbers). */
	loading: Record<PostureKey, boolean>
	errors: Record<PostureKey, string | null>
}>()

const cells = computed(() => buildPostureCells({ alerts: alertCounts, cases: caseCounts, agents: agentCounts }))
</script>

<style lang="scss" scoped>
.posture-strip {
	display: grid;
	grid-template-columns: 1fr;
	overflow: hidden;

	@media (min-width: 900px) {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}

	&__cell + &__cell {
		border-top: 1px solid var(--border-color);

		@media (min-width: 900px) {
			border-top: none;
			border-left: 1px solid var(--border-color);
		}
	}
}
</style>
