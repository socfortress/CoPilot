<template>
	<div class="page flex flex-col gap-4">
		<div class="flex flex-wrap items-center gap-3">
			<n-button quaternary class="self-start" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<Badge v-if="headerReview" type="splitted">
				<template #label>Customer</template>
				<template #value>{{ headerReview.customer_code }}</template>
			</Badge>
			<Badge v-if="headerReview" type="splitted">
				<template #label>Alert</template>
				<template #value>#{{ headerReview.alert_id }}</template>
			</Badge>
			<Badge v-if="headerReview" type="splitted">
				<template #label>Report</template>
				<template #value>#{{ headerReview.report_id }}</template>
			</Badge>
		</div>

		<FeedbackDashboardRecentReviewDetail
			v-if="reviewIdParam != null"
			:review-id="reviewIdParam"
			@loaded="onLoadedReview"
		/>
		<n-empty v-else description="Invalid review ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystReview } from "@/types/ai-analyst"
import { NButton, NEmpty } from "naive-ui"
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import FeedbackDashboardRecentReviewDetail from "@/components/aiAnalyst/Feedback/FeedbackDashboardRecentReviewDetail.vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const headerReview = ref<AiAnalystReview | null>(null)

const reviewIdParam = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})

function onLoadedReview(review: AiAnalystReview) {
	headerReview.value = review
}

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "AiAnalyst" })
}
</script>
