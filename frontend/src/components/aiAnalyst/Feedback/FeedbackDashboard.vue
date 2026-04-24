<template>
	<div class="feedback-dashboard @container flex flex-col gap-5">
		<FeedbackDashboardToolbar v-model:customer="customer" v-model:loading="loading" @refresh="loadStats()" />

		<n-spin :show="loading" class="min-h-40">
			<div v-if="!customer" class="pt-6 text-center">
				<n-empty description="Pick a customer to see their review feedback" />
			</div>

			<div v-else-if="stats" class="flex flex-col gap-5">
				<FeedbackDashboardMetricTiles :stats />
				<FeedbackDashboardTemplateChoiceDistribution :stats />
				<FeedbackDashboardTemplateTable :stats />
				<FeedbackDashboardRecentReviews :stats />
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystReviewStats } from "@/types/aiAnalyst.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import FeedbackDashboardMetricTiles from "./FeedbackDashboardMetricTiles.vue"
import FeedbackDashboardRecentReviews from "./FeedbackDashboardRecentReviews.vue"
import FeedbackDashboardTemplateChoiceDistribution from "./FeedbackDashboardTemplateChoiceDistribution.vue"
import FeedbackDashboardTemplateTable from "./FeedbackDashboardTemplateTable.vue"
import FeedbackDashboardToolbar from "./FeedbackDashboardToolbar.vue"

const message = useMessage()
const customer = ref<string | null>(null)
const loading = ref(false)
const stats = ref<AiAnalystReviewStats | null>(null)

async function loadStats() {
	if (!customer.value) {
		stats.value = null
		return
	}
	loading.value = true
	try {
		const res = await Api.aiAnalyst.getReviewStats(customer.value, 10)
		if (res.data.success) {
			stats.value = res.data
		} else {
			message.warning(res.data.message || "Failed to load stats")
			stats.value = null
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to load stats")
		stats.value = null
	} finally {
		loading.value = false
	}
}

// Refetch stats on actual customer changes only. Wiring via @update:value on
// the select is fragile — naive-ui can fire update:value when the options
// prop identity churns, which would loop the stats endpoint. watch() only
// fires on real value changes, so programmatic and user-driven picks behave
// the same and options churn is ignored.
watch(customer, () => {
	loadStats()
})
</script>
