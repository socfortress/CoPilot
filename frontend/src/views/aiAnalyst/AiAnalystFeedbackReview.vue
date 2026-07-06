<template>
	<div class="page">
		<FeedbackDashboardRecentReviewDetail v-if="reviewId != null" :review-id />
		<n-empty v-else description="Invalid review ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"
import FeedbackDashboardRecentReviewDetail from "@/components/aiAnalyst/Feedback/FeedbackDashboardRecentReviewDetail.vue"

const route = useRoute()

const reviewId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})
</script>
