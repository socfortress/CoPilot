<template>
	<div class="page flex flex-col gap-4">
		<div class="flex flex-wrap items-center gap-3">
			<n-button quaternary class="self-start" @click="goBack(routeAiAnalystFeedbackReview())">
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
import { ref } from "vue"
import FeedbackDashboardRecentReviewDetail from "@/components/aiAnalyst/Feedback/FeedbackDashboardRecentReviewDetail.vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeAiAnalystFeedbackReview } = useNavigation()

const BackIcon = "carbon:arrow-left"

const headerReview = ref<AiAnalystReview | null>(null)

const reviewIdParam = useRouteIdParam("id")

function onLoadedReview(review: AiAnalystReview) {
	headerReview.value = review
}
</script>
