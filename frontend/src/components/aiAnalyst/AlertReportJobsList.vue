<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-2">
			<template v-if="jobs.length">
				<n-card v-for="job of jobs" :key="job.id" size="small" embedded>
					<div class="flex flex-wrap items-center gap-3">
						<Badge type="splitted" bright :color="statusColor(job.status)">
							<template #label>Status</template>
							<template #value>{{ job.status }}</template>
						</Badge>
						<Badge type="splitted">
							<template #label>Triggered By</template>
							<template #value>{{ job.triggered_by }}</template>
						</Badge>
						<Badge v-if="job.alert_type" type="splitted">
							<template #label>Alert Type</template>
							<template #value>{{ job.alert_type }}</template>
						</Badge>
						<Badge v-if="job.template_used" type="splitted">
							<template #label>Template</template>
							<template #value>{{ job.template_used }}</template>
						</Badge>
					</div>
					<div class="mt-2 flex flex-wrap items-center gap-3 text-sm opacity-70">
						<span>
							<Icon :name="TimeIcon" :size="12" class="relative top-0.5" />
							Created: {{ formatDate(job.created_at, dFormats.datetime) }}
						</span>
						<span v-if="job.started_at">Started: {{ formatDate(job.started_at, dFormats.datetime) }}</span>
						<span v-if="job.completed_at">
							Completed: {{ formatDate(job.completed_at, dFormats.datetime) }}
						</span>
					</div>
					<div v-if="job.error_message" class="mt-2">
						<n-alert type="error" :bordered="false" size="small">
							{{ job.error_message }}
						</n-alert>
					</div>
				</n-card>
			</template>
			<n-empty v-else-if="!loading" description="No jobs found for this alert" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystJob } from "@/types/aiAnalyst.d"
import { NAlert, NCard, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	alertId: number
}>()

const { alertId } = toRefs(props)

const TimeIcon = "carbon:time"

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const jobs = ref<AiAnalystJob[]>([])

function statusColor(status: string) {
	if (status === "completed") return "success"
	if (status === "running") return "warning"
	if (status === "failed") return "danger"
	return undefined
}

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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
