<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeAiAnalystFeedbackReview()">
			<template v-if="headerReview" #meta>
				<Badge type="splitted">
					<template #label>Customer</template>
					<template #value>{{ headerReview.customer_code }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Alert</template>
					<template #value>#{{ headerReview.alert_id }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Report</template>
					<template #value>#{{ headerReview.report_id }}</template>
				</Badge>
			</template>
		</DetailPageHeader>

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
import { NEmpty } from "naive-ui"
import { ref } from "vue"
import FeedbackDashboardRecentReviewDetail from "@/components/aiAnalyst/Feedback/FeedbackDashboardRecentReviewDetail.vue"
import Badge from "@/components/common/Badge.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeAiAnalystFeedbackReview } = useNavigation()

const headerReview = ref<AiAnalystReview | null>(null)

const reviewIdParam = useRouteIdParam("id")

function onLoadedReview(review: AiAnalystReview) {
	headerReview.value = review
}
</script>
