<template>
	<div class="scheduler-list">
		<n-spin :show="loading" class="min-h-48">
			<div class="min-h-52">
				<template v-if="jobs.length">
					<JobCard v-for="job of jobs" :key="job.id" :job="job" class="mb-2" />
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Job } from "@/types/scheduler.d"
import Api from "@/api"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import JobCard from "./Item.vue"

const message = useMessage()
const loadingJobs = ref(false)
const jobs = ref<Job[]>([])
const loading = computed(() => loadingJobs.value)

function getData() {
	loadingJobs.value = true

	Api.scheduler
		.getAllJobs()
		.then(res => {
			if (res.data.success) {
				jobs.value = res.data.jobs || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingJobs.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
