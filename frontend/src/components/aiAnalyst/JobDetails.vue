<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedJob" size="small" :embedded>
			<template v-if="!embedded" #headerMain>
				<span class="font-mono text-sm">{{ resolvedJob.id }}</span>
			</template>

			<template #default>
				<div class="flex flex-wrap items-center justify-between">
					<div class="flex flex-wrap items-center gap-3">
						<Badge type="splitted" bright :color="statusColor(resolvedJob.status)">
							<template #label>Status</template>
							<template #value>{{ resolvedJob.status }}</template>
						</Badge>
						<Badge type="splitted">
							<template #label>Triggered By</template>
							<template #value>{{ resolvedJob.triggered_by }}</template>
						</Badge>
						<Badge v-if="resolvedJob.alert_type" type="splitted">
							<template #label>Alert Type</template>
							<template #value>{{ resolvedJob.alert_type }}</template>
						</Badge>
						<Badge v-if="resolvedJob.template_used" type="splitted">
							<template #label>Template</template>
							<template #value>{{ resolvedJob.template_used }}</template>
						</Badge>
						<template v-if="!embedded">
							<Badge type="splitted">
								<template #label>Alert</template>
								<template #value>#{{ resolvedJob.alert_id }}</template>
							</Badge>
							<Badge type="splitted">
								<template #label>Customer</template>
								<template #value>{{ resolvedJob.customer_code }}</template>
							</Badge>
						</template>
					</div>

					<template v-if="$slots.headerExtra">
						<slot name="headerExtra" />
					</template>
				</div>
			</template>

			<template v-if="resolvedJob.error_message" #mainExtra>
				<n-alert type="error" :bordered="false" size="small">
					{{ resolvedJob.error_message }}
				</n-alert>
			</template>

			<template #footer>
				<div ref="timelineRef">
					<n-timeline :horizontal="horizontalMode">
						<n-timeline-item title="Created">
							<div class="text-secondary font-mono text-sm">
								{{ formatDate(resolvedJob.created_at, dFormats.datetime, { tz: true }) }}
							</div>
						</n-timeline-item>
						<n-timeline-item v-if="resolvedJob.started_at" title="Started" type="warning">
							<div class="text-secondary font-mono text-sm">
								{{ formatDate(resolvedJob.started_at, dFormats.datetime, { tz: true }) }}
							</div>
						</n-timeline-item>
						<n-timeline-item v-if="resolvedJob.completed_at" title="Completed" type="success">
							<div class="text-secondary font-mono text-sm">
								{{ formatDate(resolvedJob.completed_at, dFormats.datetime, { tz: true }) }}
							</div>
						</n-timeline-item>
					</n-timeline>
				</div>
			</template>
		</CardEntity>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystJob } from "@/types/ai-analyst"
import type { ApiError } from "@/types/common"
import { useElementSize } from "@vueuse/core"
import axios from "axios"
import { NAlert, NSpin, NTimeline, NTimelineItem, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = withDefaults(
	defineProps<{
		job?: AiAnalystJob | null
		jobId?: string | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: AiAnalystJob): void
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const fetchedJob = ref<AiAnalystJob | null>(null)
const timelineRef = useTemplateRef("timelineRef")
const { width: timelineWidth } = useElementSize(timelineRef)

let abortController: AbortController | null = null

const resolvedJob = computed(() => props.job ?? fetchedJob.value)
const horizontalMode = computed(() => timelineWidth.value > 550)

function statusColor(status: string) {
	if (status === "completed") return "success"
	if (status === "running") return "warning"
	if (status === "failed") return "danger"
	return undefined
}

function loadJob(jobId: string) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.aiAnalyst
		.getJob(jobId, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.job) {
				fetchedJob.value = res.data.job
				emit("loaded", res.data.job)
			} else {
				message.warning(res.data?.message || "Job not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load job.")
				loading.value = false
			}
		})
}

watch(
	() => [props.job, props.jobId] as const,
	([job, jobId]) => {
		if (job) {
			abortController?.abort()
			fetchedJob.value = null
			loading.value = false
			return
		}

		if (jobId) {
			loadJob(jobId)
			return
		}

		abortController?.abort()
		fetchedJob.value = null
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedJob })
</script>
