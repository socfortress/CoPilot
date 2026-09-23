<template>
	<div class="page overview flex flex-col gap-6">
		<OverviewHeader :last-updated :refreshing="isRefreshing" @refresh="refresh()" />

		<OverviewPosture
			:alert-counts
			:case-counts
			:agent-counts
			:loading="{ alerts: loading.alerts, cases: loading.cases, agents: loading.agents }"
			:errors="{ alerts: errors.alerts, cases: errors.cases, agents: errors.agents }"
			:loaded
		/>

		<OverviewAiInsights v-if="!errors.ai" :insights :loading="!loaded && loading.ai" @updated="refresh()" />

		<div class="activity-grid grid gap-6">
			<OverviewRecentAlerts
				:alerts
				:loading="!loaded && loading.alerts"
				:error="errors.alerts"
				@retry="refresh()"
				@updated="refresh()"
			/>
			<OverviewRecentCases
				:cases
				:loading="!loaded && loading.cases"
				:error="errors.cases"
				@retry="refresh()"
				@updated="refresh()"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount } from "vue"
import OverviewAiInsights from "@/components/overview/OverviewAiInsights.vue"
import OverviewHeader from "@/components/overview/OverviewHeader.vue"
import OverviewPosture from "@/components/overview/OverviewPosture.vue"
import OverviewRecentAlerts from "@/components/overview/OverviewRecentAlerts.vue"
import OverviewRecentCases from "@/components/overview/OverviewRecentCases.vue"
import { useOverviewData } from "@/composables/overview/useOverviewData"

// Hierarchy, top to bottom: what needs attention now (posture), the AI analyst's
// read of it (when the SOC publishes findings), then what just happened (recent
// alerts and cases).
const {
	alerts,
	cases,
	alertCounts,
	caseCounts,
	agentCounts,
	insights,
	loading,
	errors,
	loaded,
	lastUpdated,
	isRefreshing,
	refresh
} = useOverviewData()

onBeforeMount(() => {
	refresh()
})
</script>

<style lang="scss" scoped>
.overview {
	.activity-grid {
		grid-template-columns: minmax(0, 1fr);

		@media (min-width: 1100px) {
			// Equal columns: both feeds carry long titles, and same-height panels read as
			// one block. Alerts sit first (left) because they are the primary feed.
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
}
</style>
