<template>
	<div class="scheduler-list">
		<n-spin :show="loading" class="min-h-48">
			<div class="list">
				<template v-if="jobs.length">
					<JobCard v-for="job of jobs" :key="job.id" :job="job" class="mb-2" />
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import JobCard from "./Item.vue"
import type { Job } from "@/types/scheduler"

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

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
