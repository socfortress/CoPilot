<template>
	<n-spin :show="loading" class="min-h-40">
		<div class="flex flex-col gap-2">
			<template v-if="jobs.length">
				<JobItem v-for="job of jobs" :key="job.id" :job />
			</template>
			<n-empty v-else-if="!loading" description="No jobs found for this alert" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystJob } from "@/types/ai-analyst"
import type { ApiError } from "@/types/common"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import JobItem from "./JobItem.vue"

const props = defineProps<{
	alertId: number
}>()

const { alertId } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const jobs = ref<AiAnalystJob[]>([])

function getData() {
	loading.value = true

	Api.aiAnalyst
		.getJobsByAlert(alertId.value)
		.then(res => {
			if (res.data.success) {
				jobs.value = res.data?.jobs || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
