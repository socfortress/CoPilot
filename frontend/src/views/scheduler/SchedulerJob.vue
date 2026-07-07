<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="router.push({ name: 'Scheduler' })">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to scheduler
		</n-button>

		<JobDetails v-if="jobId" :job-id />
		<n-empty v-else description="Invalid job ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import JobDetails from "@/components/scheduler/JobDetails.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const jobId = computed(() => {
	const id = route.params.id
	return typeof id === "string" && id.length > 0 ? id : null
})
</script>
