<template>
	<!-- Whether to show this card at all is the page's call (see Overview.vue). -->
	<OverviewPanel
		title="AI analyst findings"
		icon="carbon:ai-generate"
		:meta="
			insights.total_reports
				? `${insights.total_reports} ${insights.total_reports === 1 ? 'alert' : 'alerts'} analyzed`
				: undefined
		"
		:loading
	>
		<template #skeleton>
			<div class="ai-grid grid" aria-busy="true">
				<div class="summary border-default flex flex-col gap-4 p-5">
					<div class="flex h-[29px] items-center gap-2">
						<n-skeleton :height="26" :width="28" :sharp="false" />
						<n-skeleton :height="10" :width="96" :sharp="false" />
					</div>
					<n-skeleton :height="6" :sharp="false" />
					<div class="flex flex-col gap-1.5">
						<div v-for="n of 2" :key="n" class="flex h-4 items-center justify-between gap-3">
							<n-skeleton :height="9" :width="n === 1 ? '38%' : '52%'" :sharp="false" />
							<n-skeleton :height="9" :width="10" :sharp="false" />
						</div>
					</div>
				</div>
				<OverviewActivityList
					:items="[]"
					skeleton
					:skeleton-rows
					:skeleton-detail-lines="[2]"
					class="min-w-0"
				/>
			</div>
		</template>

		<div class="ai-grid grid">
			<div class="summary border-default flex flex-col gap-4 p-5">
				<div class="flex items-baseline gap-2">
					<span class="headline font-mono tabular-nums">{{ attentionCount }}</span>
					<span class="text-secondary text-sm">high or critical</span>
				</div>

				<StatusBar :segments />

				<ul class="m-0 flex list-none flex-col gap-1.5 p-0">
					<li
						v-for="segment of segments"
						:key="segment.key"
						class="text-secondary flex items-center justify-between gap-3 text-xs"
					>
						<span class="flex items-center gap-1.5">
							<span class="dot" :style="{ backgroundColor: colorVar(segment.color) }" />
							{{ segment.label }}
						</span>
						<div class="bg-border h-px grow"></div>
						<span class="text-default font-mono tabular-nums">{{ segment.value }}</span>
					</li>
				</ul>
			</div>

			<OverviewActivityList :items="findings" class="min-w-0">
				<template #action="{ item }">
					<AlertDetailsButton :alert-id="item.id" size="tiny" @status-updated="emit('updated')" />
				</template>
			</OverviewActivityList>
		</div>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { ActivityItem } from "./OverviewActivityList.vue"
import type { StatusSegment } from "./status"
import type { AiInsights } from "@/types/aiReports"
import { NSkeleton } from "naive-ui"
import { computed } from "vue"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import { useAuthStore } from "@/stores/auth"
import OverviewActivityList from "./OverviewActivityList.vue"
import OverviewPanel from "./OverviewPanel.vue"
import { colorVar, severityColor } from "./status"
import StatusBar from "./StatusBar.vue"

const { insights, skeletonRows = 3 } = defineProps<{
	insights: AiInsights
	loading: boolean
	/** How many finding rows the placeholder shows: the page passes the last known count. */
	skeletonRows?: number
}>()

const emit = defineEmits<{
	/** An alert changed from the details modal: the page reloads its numbers. */
	(e: "updated"): void
}>()

// Severity buckets in display order; anything the backend reports outside this
// list (including the "Unknown" bucket) is appended after them.
const SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"]

const authStore = useAuthStore()
const showCustomer = computed(() => authStore.accessibleCustomerCodes.length > 1)

const segments = computed<StatusSegment[]>(() =>
	Object.entries(insights.severity_counts)
		.filter(([, count]) => count > 0)
		.sort(([a], [b]) => {
			const indexA = SEVERITY_ORDER.indexOf(a)
			const indexB = SEVERITY_ORDER.indexOf(b)
			return (indexA === -1 ? SEVERITY_ORDER.length : indexA) - (indexB === -1 ? SEVERITY_ORDER.length : indexB)
		})
		.map(([severity, count]) => ({
			key: severity,
			label: severity.toLowerCase(),
			value: count,
			color: severityColor(severity)
		}))
)

// Same row as Recent alerts: the severity takes the place of the workflow status and
// the AI summary is the detail, with room for two lines.
const findings = computed<ActivityItem[]>(() =>
	insights.recent.map(item => ({
		id: item.alert_id,
		title: item.alert_name,
		detail: item.summary?.trim() || undefined,
		detailLines: 2,
		status: {
			label: (item.severity_assessment || "unknown").toLowerCase(),
			color: severityColor(item.severity_assessment)
		},
		time: item.report_created_at,
		meta: showCustomer.value ? [item.customer_code] : []
	}))
)

const attentionCount = computed(() =>
	segments.value
		.filter(segment => ["critical", "high"].includes(segment.key.toLowerCase()))
		.reduce((sum, s) => sum + s.value, 0)
)
</script>

<style lang="scss" scoped>
.ai-grid {
	grid-template-columns: 1fr;

	@media (min-width: 900px) {
		grid-template-columns: 17rem minmax(0, 1fr);

		.summary {
			border-right: 1px solid var(--border-color);
		}
	}

	@media (max-width: 899px) {
		.summary {
			border-bottom: 1px solid var(--border-color);
		}
	}

	.headline {
		font-size: 1.75rem;
		font-weight: 600;
		line-height: 1;
		letter-spacing: -0.03em;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 2px;
	}
}
</style>
