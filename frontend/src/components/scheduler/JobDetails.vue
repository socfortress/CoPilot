<template>
	<n-spin :show="loading">
		<div v-if="resolvedJob" class="flex flex-col gap-4">
			<CardEntity embedded>
				<template #headerMain>{{ resolvedJob.id }}</template>
				<template #headerExtra>
					<n-tag :type="resolvedJob.enabled ? 'success' : 'warning'" size="small">
						{{ resolvedJob.enabled ? "Enabled" : "Paused" }}
					</n-tag>
				</template>
				<template #default>
					<p>{{ resolvedJob.description || "No description" }}</p>
				</template>
				<template #footerMain>
					<div class="flex flex-wrap items-center gap-3">
						<Badge type="splitted" color="primary">
							<template #label>Name</template>
							<template #value>{{ resolvedJob.name }}</template>
						</Badge>
						<Badge type="splitted" color="primary">
							<template #label>Interval</template>
							<template #value>
								{{ resolvedJob.time_interval }}
								{{ resolvedJob.time_interval === 1 ? "minute" : "minutes" }}
							</template>
						</Badge>
						<Badge type="splitted">
							<template #label>Last success</template>
							<template #value>
								{{
									resolvedJob.last_success
										? formatDate(resolvedJob.last_success, dFormats.datetimesec)
										: "—"
								}}
							</template>
						</Badge>
						<Badge v-if="resolvedJob.enabled" type="splitted">
							<template #label>Next run</template>
							<template #value>
								<NextJobTimeTooltip :job-id="resolvedJob.id" />
							</template>
						</Badge>
					</div>
				</template>
			</CardEntity>

			<n-card size="small" title="Actions" embedded>
				<JobActions :job="resolvedJob" />
			</n-card>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Job } from "@/types/scheduler"
import axios from "axios"
import { NCard, NSpin, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import JobActions from "./JobActions.vue"
import NextJobTimeTooltip from "./NextJobTimeTooltip.vue"

const props = defineProps<{
	job?: Job | null
	jobId?: string | null
}>()

const emit = defineEmits<{
	(e: "loaded", value: Job): void
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const fetchedJob = ref<Job | null>(null)

let abortController: AbortController | null = null

const resolvedJob = computed(() => props.job ?? fetchedJob.value)

function loadJob(jobId: string) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.scheduler
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

function reload() {
	const id = resolvedJob.value?.id
	if (!id) return
	if (props.job) return
	loadJob(id)
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

defineExpose({ loading, resolvedJob, reload })
</script>
