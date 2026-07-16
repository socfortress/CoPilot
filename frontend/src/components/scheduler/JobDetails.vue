<template>
	<n-spin :show="loading">
		<div v-if="resolvedJob" class="flex flex-col gap-4">
			<CardEntity embedded>
				<template #headerMain>
					<span class="text-default text-lg font-bold">
						{{ resolvedJob.id }}
					</span>
				</template>
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
import type { Job } from "@/types/scheduler"
import { NCard, NSpin, NTag } from "naive-ui"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useSettingsStore } from "@/stores/settings"
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

const dFormats = useSettingsStore().dateFormat

const {
	loading,
	entity: resolvedJob,
	reload: reloadJob
} = useEntityDetails<Job, string>({
	entity: () => props.job,
	id: () => props.jobId || null,
	fetch: (id, signal) =>
		Api.scheduler.getJob(id, signal).then(res => ({
			entity: res.data.success ? (res.data.job ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Job not found.",
	errorMessage: "Failed to load job.",
	onLoaded: value => emit("loaded", value)
})

function reload() {
	if (!resolvedJob.value?.id) return
	if (props.job) return
	reloadJob()
}

defineExpose({ loading, resolvedJob, reload })
</script>
