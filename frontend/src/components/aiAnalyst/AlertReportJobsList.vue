<template>
	<n-spin :show="loading" class="min-h-40">
		<div ref="jobsListRef" class="flex flex-col gap-2">
			<template v-if="jobs.length">
				<CardEntity v-for="job of jobs" :key="job.id" size="small" embedded>
					<template #default>
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
					</template>
					<template v-if="job.error_message" #mainExtra>
						<n-alert type="error" :bordered="false" size="small">
							{{ job.error_message }}
						</n-alert>
					</template>
					<template #footer>
						<n-timeline :horizontal="horizontalMode">
							<n-timeline-item title="Created">
								<div class="text-secondary font-mono text-sm">
									{{ formatDate(job.created_at, dFormats.datetime).toString() }}
								</div>
							</n-timeline-item>
							<n-timeline-item v-if="job.started_at" title="Started" type="warning">
								<div class="text-secondary font-mono text-sm">
									{{ formatDate(job.started_at, dFormats.datetime).toString() }}
								</div>
							</n-timeline-item>
							<n-timeline-item v-if="job.completed_at" title="Completed" type="success">
								<div class="text-secondary font-mono text-sm">
									{{ formatDate(job.completed_at, dFormats.datetime).toString() }}
								</div>
							</n-timeline-item>
						</n-timeline>
					</template>
				</CardEntity>
			</template>
			<n-empty v-else-if="!loading" description="No jobs found for this alert" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystJob } from "@/types/aiAnalyst.d"
import { useElementSize } from "@vueuse/core"
import { NAlert, NEmpty, NSpin, NTimeline, NTimelineItem, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, useTemplateRef } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	alertId: number
}>()

const { alertId } = toRefs(props)

const { width: jobsListWidthRef } = useElementSize(useTemplateRef("jobsListRef"))
const horizontalMode = computed(() => jobsListWidthRef.value > 550)
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
