<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeSchedulerJob()" />

		<JobDetails v-if="jobId" :job-id />
		<n-empty v-else description="Invalid job ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import JobDetails from "@/components/scheduler/JobDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeSchedulerJob } = useNavigation()

const jobId = useRouteParam("id")
</script>
