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

		<OverviewAiInsights
			v-if="showAiInsights"
			:insights
			:loading="!loaded && loading.ai"
			:skeleton-rows="aiRowsHint || undefined"
			@updated="refresh()"
		/>

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
import { useSessionStorage } from "@vueuse/core"
import { computed, onBeforeMount, watch } from "vue"
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

/**
 * The AI card only exists when the SOC has published findings, which is unknown
 * until the first response. Showing it only then pushes the whole activity area
 * down; always showing a placeholder makes it collapse for customers without AI.
 * So the page remembers, per session, how many findings the card last showed and
 * reserves exactly that space while loading.
 */
const aiRowsHint = useSessionStorage("overview.ai-findings-rows", 0)

const showAiInsights = computed(() => {
	if (errors.ai) return false
	return loaded.value ? insights.value.total_reports > 0 : aiRowsHint.value > 0
})

// Refreshed on every completed load, including refreshes and filter changes.
watch([loaded, insights], ([isLoaded, current]) => {
	if (!isLoaded || errors.ai) return
	aiRowsHint.value = current.total_reports > 0 ? current.recent.length : 0
})

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
