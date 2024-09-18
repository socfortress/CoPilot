<template>
	<div class="job-actions flex flex-col gap-3" :class="{ '!flex-row': inline }">
		<div class="flex gap-3 items-center">
			<n-button
				:size="size"
				:type="job.enabled ? 'warning' : 'success'"
				secondary
				:loading="loadingAction"
				class="grow"
				@click="toggleState()"
			>
				<template #icon>
					<Icon :name="job.enabled ? PauseIcon : StartIcon"></Icon>
				</template>
				{{ job.enabled ? "Pause" : "Start" }}
			</n-button>

			<NextTooltip v-if="job.enabled && !inline" :job-id="job.id" />
		</div>
		<div class="flex gap-3 items-center">
			<n-button :size="size" type="success" secondary :loading="loadingRun" @click="run()">
				<template #icon>
					<Icon :name="RunIcon"></Icon>
				</template>
				Run once
			</n-button>
			<n-button :size="size" secondary :loading="loadingUpdate" @click="showForm = true">
				<template #icon>
					<Icon :name="UpdatedIcon"></Icon>
				</template>
			</n-button>

			<NextTooltip v-if="job.enabled && inline" :job-id="job.id" />
		</div>
	</div>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(450px, 90vw)', overflow: 'hidden' }"
		:title="`Update ${job.name}`"
		:bordered="false"
		segmented
	>
		<JobForm :job="job" @updated="update($event)" />
	</n-modal>
</template>

<script setup lang="ts">
import type { UpdateJobPayload } from "@/api/endpoints/scheduler"
import type { Job } from "@/types/scheduler.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import JobForm from "./JobForm.vue"
import NextTooltip from "./NextTooltip.vue"

const props = defineProps<{ job: Job; size?: Size; inline?: boolean }>()
const { job, size, inline } = toRefs(props)

const StartIcon = "material-symbols:autoplay"
const PauseIcon = "carbon:pause-filled"
const RunIcon = "carbon:play"
const UpdatedIcon = "carbon:settings-adjust"

const message = useMessage()
const showForm = ref(false)
const loadingRun = ref(false)
const loadingAction = ref(false)
const loadingUpdate = ref(false)

function toggleState() {
	loadingAction.value = true

	const action = job.value.enabled ? "pause" : "start"

	Api.scheduler
		.jobAction(job.value.id, action)
		.then(res => {
			if (res.data.success) {
				job.value.enabled = action === "start"
				message.success(res.data?.message || "Job updated successfully.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAction.value = false
		})
}

function run() {
	loadingRun.value = true

	Api.scheduler
		.jobAction(job.value.id, "run")
		.then(res => {
			if (res.data.success) {
				// TODO: check timezone with Taylor
				job.value.last_success = new Date()
				message.success(res.data?.message || "Job executed successfully.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingRun.value = false
		})
}

function update(payload: UpdateJobPayload) {
	showForm.value = false
	job.value.time_interval = payload.time_interval
}
</script>
