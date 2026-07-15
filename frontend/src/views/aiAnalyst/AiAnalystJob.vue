<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeAiAnalystJob()" />

		<JobDetails v-if="jobId" :job-id :embedded="false" />
		<n-empty v-else description="Invalid job ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import JobDetails from "@/components/aiAnalyst/JobDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAiAnalystJob } = useNavigation()

const jobId = useRouteParam("id")
</script>
