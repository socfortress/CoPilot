<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<CoverageGapDetails v-if="techniqueId" :technique-id :embedded="false" />
		<n-empty v-else description="Invalid technique ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import CoverageGapDetails from "@/components/detectionCatalog/CoverageGapDetails.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const techniqueId = computed(() => {
	const raw = route.params.techniqueId
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "DetectionCatalog" })
}
</script>
