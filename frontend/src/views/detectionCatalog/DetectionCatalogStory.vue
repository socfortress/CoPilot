<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="routeDetectionCatalogStory().navigate()">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to catalog
		</n-button>

		<StoryDetail v-if="storyName" :story-name @error="handleError" />
		<n-empty v-else description="Invalid story name" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import StoryDetail from "@/components/detectionCatalog/StoryDetail.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeDetectionCatalogStory } = useNavigation()
const message = useMessage()

const BackIcon = "carbon:arrow-left"

const storyName = useRouteParam("name")

function handleError(errorMessage: string) {
	message.warning(errorMessage)
}
</script>
