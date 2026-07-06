<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="router.push({ name: 'DetectionCatalog' })">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to catalog
		</n-button>

		<StoryDetail v-if="storyName" :story-name="storyName" @error="handleError" />
		<n-empty v-else description="Invalid story name" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty, useMessage } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import StoryDetail from "@/components/detectionCatalog/StoryDetail.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()
const message = useMessage()

const BackIcon = "carbon:arrow-left"

const storyName = computed(() => {
	const raw = route.params.name
	if (!raw) return null
	return Array.isArray(raw) ? raw.join("/") : String(raw)
})

function handleError(errorMessage: string) {
	message.warning(errorMessage)
}
</script>
