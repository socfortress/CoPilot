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
					@toggle-enabled="enabled => toggleEnabled(schedule, enabled)"
					@edit="openEditModal(schedule)"
					@delete="deleteSchedule(schedule)"
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
import type { SnapshotScheduleResponse } from "@/types/snapshots"
import { NButton, NEmpty, NModal, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SnapshotScheduleCard from "./SnapshotScheduleCard.vue"
import SnapshotScheduleForm from "./SnapshotScheduleForm.vue"

const AddIcon = "carbon:add"

const message = useMessage()
const loading = ref(false)
const schedules = ref<SnapshotScheduleResponse[]>([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const selectedSchedule = ref<SnapshotScheduleResponse | null>(null)

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
	} catch (error: any) {
		message.error(error.message || "Failed to update schedule")
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
	} catch (error: any) {
		message.error(error.message || "Failed to delete schedule")
	}
}

async function fetchSchedules() {
	loading.value = true
	try {
		const response = await Api.snapshots.getSchedules()
		if (response.data.success) {
			schedules.value = response.data.schedules
		} else {
			message.error(response.data.message)
		}
	} catch (error: any) {
		message.error(error.message || "Failed to fetch schedules")
	} finally {
		loading.value = false
	}
}

function onScheduleCreated() {
	showCreateModal.value = false
	fetchSchedules()
	message.success("Schedule created successfully")
}

function onScheduleUpdated() {
	showEditModal.value = false
	fetchSchedules()
	message.success("Schedule updated successfully")
}

onBeforeMount(() => {
	fetchSchedules()
})
</script>
