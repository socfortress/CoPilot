<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeDetectionCatalogDetection()" />

		<RuleCardContent v-if="detectionId" :rule-id="detectionId" />
		<n-empty v-else description="Invalid detection ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import RuleCardContent from "@/components/copilotSearches/RuleCardContent.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeDetectionCatalogDetection } = useNavigation()

const detectionId = useRouteParam("id")
</script>
