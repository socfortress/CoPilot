<template>
	<CardEntity>
		<template #headerMain>{{ job.id }}</template>
		<template #headerExtra>
			<n-tooltip placement="top-end">
				<template #trigger>
					<div class="flex items-center gap-2">
						{{ formatDate(job.last_success, dFormats.datetimesec) }}
						<Icon :name="TimeIcon"></Icon>
					</div>
				</template>
				Last success time
			</n-tooltip>
		</template>

		<template #default>
			{{ job.description }}
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-3">
				<Badge type="splitted" color="primary">
					<template #label>Interval</template>
					<template #value>
						{{ job.time_interval }} {{ job.time_interval === 1 ? "minute" : "minutes" }}
					</template>
				</Badge>
				<Badge v-if="job.enabled" type="splitted" color="primary">
					<template #label>Next run time</template>
					<template #value>
						<div class="hover:text-primary flex h-full cursor-help items-center">
							<NextJobTimeTooltip :job-id="job.id" />
						</div>
					</template>
				</Badge>
			</div>
		</template>
		<template #footerExtra>
			<div class="flex flex-row flex-wrap gap-3">
				<JobActions :job="job" size="small" />
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { Job } from "@/types/scheduler.d"
import { NTooltip } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import JobActions from "./JobActions.vue"
import NextJobTimeTooltip from "./NextJobTimeTooltip.vue"

const { job } = defineProps<{ job: Job }>()

const TimeIcon = "carbon:time"

const dFormats = useSettingsStore().dateFormat
</script>
