<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeDetectionCatalogStory()" />

		<StoryDetail v-if="storyName" :story-name @error="handleError" />
		<n-empty v-else description="Invalid story name" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty, useMessage } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import StoryDetail from "@/components/detectionCatalog/StoryDetail.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeDetectionCatalogStory } = useNavigation()
const message = useMessage()

const storyName = useRouteParam("name")

function handleError(errorMessage: string) {
	message.warning(errorMessage)
}
</script>
