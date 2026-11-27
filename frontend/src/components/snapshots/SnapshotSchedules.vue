<template>
	<div class="flex flex-col gap-4">
		<div>
			<n-button type="primary" size="small" @click="showCreateModal = true">
				<template #icon>
					<Icon :name="AddIcon" :size="16" />
				</template>
				Create Schedule
			</n-button>
		</div>

		<n-spin :show="loading">
			<div v-if="schedules.length" class="flex flex-col gap-3">
				<SnapshotScheduleCard
					v-for="schedule in schedules"
					:key="schedule.id"
					:schedule
					:running="runningIds.has(schedule.id)"
					@toggle-enabled="enabled => toggleEnabled(schedule, enabled)"
					@edit="openEditModal(schedule)"
					@delete="deleteSchedule(schedule)"
					@run="runSchedule(schedule)"
				/>
			</div>

			<n-empty
				v-else-if="!loading"
				description="No snapshot schedules configured"
				class="min-h-48 justify-center"
			/>
		</n-spin>

		<n-modal v-model:show="showCreateModal" preset="card" title="Create Snapshot Schedule" class="max-w-160!">
			<SnapshotScheduleForm @success="onScheduleCreated" @cancel="showCreateModal = false" />
		</n-modal>

		<n-modal v-model:show="showEditModal" preset="card" title="Edit Snapshot Schedule" class="max-w-160!">
			<SnapshotScheduleForm
				:schedule="selectedSchedule"
				@success="onScheduleUpdated"
				@cancel="showEditModal = false"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common.ts"
import type { FlaskBaseResponse } from "@/types/flask"
import type { ScheduleRunResponse, SnapshotScheduleResponse } from "@/types/snapshots"
import { NButton, NEmpty, NModal, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils/index.ts"
import SnapshotScheduleCard from "./SnapshotScheduleCard.vue"
import SnapshotScheduleForm from "./SnapshotScheduleForm.vue"

const AddIcon = "carbon:add"

const message = useMessage()
const loading = ref(false)
const schedules = ref<SnapshotScheduleResponse[]>([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const selectedSchedule = ref<SnapshotScheduleResponse | null>(null)
/** Schedules a Run now is under way for. */
const runningIds = ref(new Set<number>())

function openEditModal(schedule: SnapshotScheduleResponse) {
	selectedSchedule.value = schedule
	showEditModal.value = true
}

async function toggleEnabled(schedule: SnapshotScheduleResponse, enabled: boolean) {
	try {
		const response = await Api.snapshots.updateSchedule(schedule.id, { enabled })
		if (response.data.success) {
			message.success(`Schedule ${enabled ? "enabled" : "disabled"}`)
			fetchSchedules()
		} else {
			message.error(response.data.message)
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to update schedule")
	}
}

async function deleteSchedule(schedule: SnapshotScheduleResponse) {
	try {
		const response = await Api.snapshots.deleteSchedule(schedule.id)
		if (response.data.success) {
			message.success("Schedule deleted")
			fetchSchedules()
		} else {
			message.error(response.data.message)
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to delete schedule")
	}
}

/** What a Run now did, in the backend's words, as a toast of its outcome's kind. */
function confirmRun(run: FlaskBaseResponse & ScheduleRunResponse) {
	const options = { duration: 8000, closable: true }
	if (run.outcome === "snapshot_started") message.success(run.message, options)
	else if (run.outcome === "nothing_new") message.info(run.message, options)
	else if (run.outcome === "no_match") message.warning(run.message, options)
	else message.error(run.message, options)
}

async function runSchedule(schedule: SnapshotScheduleResponse) {
	if (runningIds.value.has(schedule.id)) return
	runningIds.value.add(schedule.id)
	try {
		const response = await Api.snapshots.runSchedule(schedule.id)
		confirmRun(response.data)
		// The card shows the run's status, time and snapshot without reloading the list.
		const ran = response.data.schedule
		schedules.value = schedules.value.map(item => (item.id === ran.id ? ran : item))
	} catch (error) {
		const text = getApiErrorMessage(error as ApiError) || "Failed to run the schedule"
		// 409: a run of it (a scheduled one, or someone else's Run now) is under way.
		if ((error as ApiError).response?.status === 409) message.warning(text)
		else message.error(text)
	} finally {
		runningIds.value.delete(schedule.id)
	}
}

async function fetchSchedules() {
	loading.value = true
	try {
		const response = await Api.snapshots.getSchedules({})
		if (response.data.success) {
			schedules.value = response.data.schedules
		} else {
			message.error(response.data.message)
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to fetch schedules")
	} finally {
		loading.value = false
	}
}

/** The save confirmation, with how many indices the pattern matches right now when the backend counted them. */
function confirmSaved(verb: "created" | "updated", matchingIndexCount: number | null) {
	if (matchingIndexCount === 0) {
		message.warning(`Schedule ${verb}, but its index pattern matches no index right now`)
	} else if (matchingIndexCount == null) {
		message.success(`Schedule ${verb} successfully`)
	} else {
		const noun = matchingIndexCount === 1 ? "index" : "indices"
		message.success(`Schedule ${verb}: its index pattern matches ${matchingIndexCount} ${noun}`)
	}
}

function onScheduleCreated(matchingIndexCount: number | null) {
	showCreateModal.value = false
	fetchSchedules()
	confirmSaved("created", matchingIndexCount)
}

function onScheduleUpdated(matchingIndexCount: number | null) {
	showEditModal.value = false
	fetchSchedules()
	confirmSaved("updated", matchingIndexCount)
}

onBeforeMount(() => {
	fetchSchedules()
})
</script>
