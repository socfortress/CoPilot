<template>
	<!-- Whether the card appears at all is decided by the page (useAiFindingsPlaceholder). -->
	<OverviewPanel title="AI analyst findings" icon="carbon:ai-generate" :meta :loading>
		<template #skeleton>
			<div class="ai-findings">
				<AiSeveritySummarySkeleton class="ai-findings__summary" />
				<ActivityList loading :skeleton-rows :skeleton-detail-lines="[2]" />
			</div>
		</template>

		<div class="ai-findings">
			<AiSeveritySummary :severity-counts="insights.severity_counts" class="ai-findings__summary" />
			<ActivityList :items>
				<template #action="{ item }">
					<AlertDetailsButton :alert-id="item.id" size="tiny" @status-updated="emit('updated')" />
				</template>
			</ActivityList>
		</div>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { AiInsights } from "@/types/aiReports"
import { computed } from "vue"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import { useIsMultiCustomer } from "@/composables/overview/useIsMultiCustomer"
import ActivityList from "../activity/ActivityList.vue"
import { findingToActivityItem } from "../activity/mappers"
import AiSeveritySummary from "../ai/AiSeveritySummary.vue"
import AiSeveritySummarySkeleton from "../ai/AiSeveritySummarySkeleton.vue"
import OverviewPanel from "../shared/OverviewPanel.vue"

const { insights, skeletonRows = 3 } = defineProps<{
	insights: AiInsights
	loading?: boolean
	/** Placeholder rows while loading: the page passes the count it last showed. */
	skeletonRows?: number
}>()

const emit = defineEmits<{
	/** An alert changed from its details modal. */
	(e: "updated"): void
}>()

const showCustomer = useIsMultiCustomer()

const meta = computed(() => {
	const total = insights.total_reports
	return total ? `${total} ${total === 1 ? "alert" : "alerts"} analyzed` : undefined
})

const items = computed(() =>
	insights.recent.map(finding => findingToActivityItem(finding, { showCustomer: showCustomer.value }))
)
</script>

<style lang="scss" scoped>
.ai-findings {
	display: grid;
	grid-template-columns: minmax(0, 1fr);

	@media (min-width: 900px) {
		grid-template-columns: 17rem minmax(0, 1fr);
	}

	&__summary {
		border-bottom: 1px solid var(--border-color);

		@media (min-width: 900px) {
			border-bottom: none;
			border-right: 1px solid var(--border-color);
		}
	}
}
</style>
