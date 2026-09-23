<template>
	<!-- Whether the card appears at all is decided by the page (useAiFindingsPlaceholder). -->
	<OverviewPanel title="AI analyst findings" icon="carbon:ai-generate" :meta :loading>
		<template #skeleton>
			<div :class="LAYOUT">
				<AiSeveritySummarySkeleton :class="SUMMARY" />
				<ActivityList loading :skeleton-rows :skeleton-detail-lines="[2]" class="grow" />
			</div>
		</template>

		<div :class="LAYOUT">
			<AiSeveritySummary :severity-counts="insights.severity_counts" :class="SUMMARY" />
			<ActivityList :items class="grow">
				<template #action="{ item }">
					<AlertDetailsButton
						:alert-id="item.id"
						size="tiny"
						ghost
						class="flex"
						@status-updated="emit('updated')"
					/>
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

// Shared by the loaded card and its skeleton: a fixed-width summary on the left from
// lg up, stacked above the findings below that.
const LAYOUT = "flex flex-col lg:flex-row"
const SUMMARY = "border-border shrink-0 border-b lg:w-68 lg:border-r lg:border-b-0"

const showCustomer = useIsMultiCustomer()

const meta = computed(() => {
	const total = insights.total_reports
	return total ? `${total} ${total === 1 ? "alert" : "alerts"} analyzed` : undefined
})

const items = computed(() =>
	insights.recent.map(finding => findingToActivityItem(finding, { showCustomer: showCustomer.value }))
)
</script>
