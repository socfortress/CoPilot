<template>
	<div class="page overview flex flex-col gap-6">
		<OverviewHeader :last-updated :refreshing="isRefreshing || trend.loading.value" @refresh="refreshAll()" />

		<PostureStrip
			:alert-counts
			:case-counts
			:agent-counts
			:loading="showSkeleton"
			:errors
			:trend="postureTrend"
		/>

		<OverviewTrendPanel
			:trend="trend.trend.value"
			:days="trend.days.value"
			:range="trendRange"
			:loading="trend.loading.value"
			:error="trend.error.value"
			@update:range="setTrendRange"
			@retry="trend.reload()"
		/>

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
import type { PostureTrend } from "@/components/overview/posture/postureCells"
import type { OverviewTrendRange } from "@/types/portal"
import { computed, onBeforeMount } from "vue"
import { useRoute, useRouter } from "vue-router"
import OverviewHeader from "@/components/overview/OverviewHeader.vue"
import AiFindingsPanel from "@/components/overview/panels/AiFindingsPanel.vue"
import RecentAlertsPanel from "@/components/overview/panels/RecentAlertsPanel.vue"
import RecentCasesPanel from "@/components/overview/panels/RecentCasesPanel.vue"
import PostureStrip from "@/components/overview/posture/PostureStrip.vue"
import OverviewTrendPanel from "@/components/overview/trend/OverviewTrendPanel.vue"
import { DEFAULT_TREND_RANGE, parseTrendRange } from "@/components/overview/trend/trend"
import { useOverviewTrend } from "@/components/overview/trend/useOverviewTrend"
import { useAiFindingsPlaceholder } from "@/composables/overview/useAiFindingsPlaceholder"
import { useOverviewData } from "@/composables/overview/useOverviewData"

// Top to bottom: what needs attention now (posture), where it is heading (trend), the AI
// analyst's read of it (when the SOC publishes findings), then what just happened.
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

// The trend's period lives in the URL (`?trend=7d`), so a shared link opens on it.
const route = useRoute()
const router = useRouter()
const trendRange = computed(() => parseTrendRange(route.query.trend))
const trend = useOverviewTrend(trendRange)

function setTrendRange(range: OverviewTrendRange) {
	const { trend: _trend, ...query } = route.query
	router.replace({ query: range === DEFAULT_TREND_RANGE ? query : { ...query, trend: range } })
}

const postureTrend = computed<PostureTrend | null>(() => {
	const days = trend.days.value
	const data = trend.trend.value
	if (!days || !data) return null
	return {
		alerts: days.map(day => day.alerts.opened),
		cases: days.map(day => day.cases.opened),
		range: data.range,
		alertsFailed: !!data.alerts_error,
		casesFailed: !!data.cases_error
	}
})

function refreshAll() {
	refresh()
	trend.reload()
}

onBeforeMount(() => {
	refresh()
})
</script>
