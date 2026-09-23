<template>
	<div class="page overview flex flex-col gap-6">
		<OverviewHeader :last-updated :refreshing="isRefreshing" @refresh="refresh()" />

		<PostureStrip :alert-counts :case-counts :agent-counts :loading="showSkeleton" :errors />

		<AiFindingsPanel
			v-if="aiFindings.visible.value"
			:insights
			:loading="showSkeleton.ai"
			:skeleton-rows="aiFindings.skeletonRows.value"
			@updated="refresh()"
		/>

		<!--
			Equal columns from lg: both feeds carry long titles, and same-height panels
			read as one block. Alerts come first because they are the primary feed.
		-->
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<RecentAlertsPanel
				:alerts
				:loading="showSkeleton.alerts"
				:error="errors.alerts"
				@retry="refresh()"
				@updated="refresh()"
			/>
			<RecentCasesPanel
				:cases
				:loading="showSkeleton.cases"
				:error="errors.cases"
				@retry="refresh()"
				@updated="refresh()"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount } from "vue"
import OverviewHeader from "@/components/overview/OverviewHeader.vue"
import AiFindingsPanel from "@/components/overview/panels/AiFindingsPanel.vue"
import RecentAlertsPanel from "@/components/overview/panels/RecentAlertsPanel.vue"
import RecentCasesPanel from "@/components/overview/panels/RecentCasesPanel.vue"
import PostureStrip from "@/components/overview/posture/PostureStrip.vue"
import { useAiFindingsPlaceholder } from "@/composables/overview/useAiFindingsPlaceholder"
import { useOverviewData } from "@/composables/overview/useOverviewData"

// Top to bottom: what needs attention now (posture), the AI analyst's read of it
// (when the SOC publishes findings), then what just happened (alerts and cases).
const {
	alerts,
	cases,
	alertCounts,
	caseCounts,
	agentCounts,
	insights,
	errors,
	loaded,
	showSkeleton,
	lastUpdated,
	isRefreshing,
	refresh
} = useOverviewData()

const aiFindings = useAiFindingsPlaceholder({ insights, loaded, failed: () => !!errors.ai })

onBeforeMount(() => {
	refresh()
})
</script>
