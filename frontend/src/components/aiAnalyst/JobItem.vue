<template>
	<JobDetails :job>
		<template #headerExtra>
			<EntityDetailsButton size="small" :order="['open']" open-show-label :route="routeAiAnalystJob(job.id)" />
		</template>
	</JobDetails>
</template>

<script setup lang="ts">
import type { AiAnalystJob } from "@/types/ai-analyst"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/useNavigation"
import JobDetails from "./JobDetails.vue"

const { job } = defineProps<{ job: AiAnalystJob }>()

const { routeAiAnalystJob } = useNavigation()
</script>
