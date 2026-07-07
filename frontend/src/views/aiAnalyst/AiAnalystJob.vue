<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<JobDetails v-if="jobId" :job-id="jobId" :embedded="false" />
		<n-empty v-else description="Invalid job ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import JobDetails from "@/components/aiAnalyst/JobDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const jobId = computed(() => {
	const raw = route.params.id
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "AiAnalyst" })
}
</script>
