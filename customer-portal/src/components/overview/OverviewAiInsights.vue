<template>
	<!--
		Rendered only once at least one AI report exists for the visible customers,
		so deployments without the AI analyst (or customers whose auto-trigger is
		off) see no empty placeholder on the overview.
	-->
	<n-spin v-if="hasInsights" :show="loading">
		<n-card title="AI Analyst Insights" segmented content-class="flex flex-col gap-4">
			<template #header-extra>
				<Icon name="carbon:ai-generate" :size="20" class="text-primary" />
			</template>

			<div class="flex flex-wrap items-center gap-2">
				<Chip
					size="small"
					round
					:bordered="false"
					label="Alerts analyzed"
					:value="insights.total_reports"
				/>
				<Chip
					v-for="(count, severity) of severityBreakdown"
					:key="severity"
					:type="severityType(severity)"
					size="small"
					round
					:bordered="false"
					:label="severity"
					:value="count"
				/>
			</div>

			<div class="flex flex-col gap-3">
				<CardEntity
					v-for="item of insights.recent"
					:key="item.alert_id"
					size="small"
					embedded
					clickable
					hoverable
					@click="routeAlertDetails(item.alert_id).navigate()"
				>
					<template #header-main>{{ item.alert_name }}</template>
					<template #header-extra>
						<Chip
							v-if="item.severity_assessment"
							:type="severityType(item.severity_assessment)"
							size="tiny"
							round
							:bordered="false"
							:value="item.severity_assessment"
						/>
					</template>
					<template v-if="item.summary" #default>
						<div class="line-clamp-2">{{ item.summary }}</div>
					</template>
					<template #footer-main>
						<div class="text-secondary text-xs">
							{{ formatDate(item.report_created_at, dFormats.datetime) }}
						</div>
					</template>
				</CardEntity>
			</div>
		</n-card>
	</n-spin>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { AiInsights } from "@/types/aiReports"
import type { ApiError } from "@/types/common"
import { NCard, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

// Severity buckets in display order; anything the backend reports outside this
// list (including the "Unknown" bucket) is appended after them.
const SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"]

// The overview is a dense page — keep the card short so it never pushes the
// recent alerts/cases panes out of view.
const RECENT_LIMIT = 3

const dFormats = useSettingsStore().dateFormat
const { routeAlertDetails } = useNavigation()
const customerFilterStore = useCustomerFilterStore()
const message = useMessage()

const loading = ref(false)
const insights = ref<AiInsights>({ total_reports: 0, severity_counts: {}, recent: [] })

const hasInsights = computed(() => insights.value.total_reports > 0)

const severityBreakdown = computed(() => {
	const entries = Object.entries(insights.value.severity_counts).filter(([, count]) => count > 0)

	return Object.fromEntries(
		entries.sort(([a], [b]) => {
			const indexA = SEVERITY_ORDER.indexOf(a)
			const indexB = SEVERITY_ORDER.indexOf(b)
			return (indexA === -1 ? SEVERITY_ORDER.length : indexA) - (indexB === -1 ? SEVERITY_ORDER.length : indexB)
		})
	)
})

function severityType(severity: string): TagProps["type"] {
	switch (severity) {
		case "Critical":
		case "High":
			return "error"
		case "Medium":
			return "warning"
		case "Low":
			return "success"
		default:
			return "default"
	}
}

function fetchInsights() {
	loading.value = true

	Api.aiReports
		.getInsights(customerFilterStore.queryCustomerCodes, RECENT_LIMIT)
		.then(res => {
			insights.value = res.data
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError))
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	fetchInsights()
})

// Refetch whenever the global customer filter changes.
watch(() => customerFilterStore.selectedCustomerCodes, fetchInsights, { deep: true })
</script>
