<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="routeSchedulerJob().navigate()">
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
import Icon from "@/components/common/Icon.vue"
import JobDetails from "@/components/scheduler/JobDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeSchedulerJob } = useNavigation()

const BackIcon = "carbon:arrow-left"

const jobId = useRouteParam("id")
</script>
