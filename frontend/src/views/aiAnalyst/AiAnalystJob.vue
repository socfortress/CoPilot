<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack(routeAiAnalystJob())">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<JobDetails v-if="jobId" :job-id :embedded="false" />
		<n-empty v-else description="Invalid job ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import JobDetails from "@/components/aiAnalyst/JobDetails.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeAiAnalystJob } = useNavigation()

const BackIcon = "carbon:arrow-left"

const jobId = useRouteParam("id")
</script>
