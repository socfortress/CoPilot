<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack(routeDetectionCatalogDetection())">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<RuleCardContent v-if="detectionId" :rule-id="detectionId" />
		<n-empty v-else description="Invalid detection ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import RuleCardContent from "@/components/copilotSearches/RuleCardContent.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeDetectionCatalogDetection } = useNavigation()

const BackIcon = "carbon:arrow-left"

const detectionId = useRouteParam("id")
</script>
