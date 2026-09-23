<template>
	<!-- One column (cells divided horizontally) below lg, then three side by side. -->
	<section
		class="bg-default border-default divide-border grid grid-cols-1 divide-y overflow-hidden rounded-lg border lg:grid-cols-3 lg:divide-x lg:divide-y-0"
		aria-label="Security posture"
	>
		<PostureCell
			v-for="cell of cells"
			:key="cell.key"
			:cell
			:loading="loading[cell.key]"
			:error="errors[cell.key]"
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
