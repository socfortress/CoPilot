<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<ComplianceDetail v-if="framework && control" :framework :control :embedded="false" />
		<n-empty v-else description="Invalid compliance control" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import ComplianceDetail from "@/components/detectionCatalog/ComplianceDetail.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const framework = computed(() => {
	const raw = route.params.framework
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

const control = computed(() => {
	const raw = route.params.control
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
