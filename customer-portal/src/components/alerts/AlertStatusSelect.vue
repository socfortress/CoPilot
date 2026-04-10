<template>
	<n-select
		:value="selectedStatus"
		:options="statusOptions"
		:loading
		size="small"
		class="min-w-36"
		@update:value="handleStatusChange"
	/>
</template>

<script setup lang="ts">
import type { AlertStatus } from "@/api/endpoints/alerts"
import type { ApiError } from "@/types/common"
import { NSelect } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface AlertStatusUpdateSuccessPayload {
	alertId: number
	status: AlertStatus
}

export interface AlertStatusUpdateErrorPayload {
	alertId: number
	status: AlertStatus
	message: string
}

const props = defineProps<{
	alertId: number
	status: AlertStatus
}>()

const emit = defineEmits<{
	success: [payload: AlertStatusUpdateSuccessPayload]
	error: [payload: AlertStatusUpdateErrorPayload]
}>()

const statusOptions = [
	{ label: "Open", value: "OPEN" },
	{ label: "In Progress", value: "IN_PROGRESS" },
	{ label: "Closed", value: "CLOSED" }
]

const selectedStatus = ref<AlertStatus>(props.status)
const loading = ref(false)

watch(
	() => props.status,
	newStatus => {
		selectedStatus.value = newStatus
	}
)

async function handleStatusChange(value: string) {
	if (loading.value || value === selectedStatus.value) return

	const previousStatus = selectedStatus.value
	selectedStatus.value = value as AlertStatus
	loading.value = true

	try {
		await Api.alerts.updateAlertStatus(props.alertId, selectedStatus.value)
		emit("success", {
			alertId: props.alertId,
			status: selectedStatus.value
		})
	} catch (err) {
		selectedStatus.value = previousStatus
		emit("error", {
			alertId: props.alertId,
			status: previousStatus,
			message: getApiErrorMessage(err as ApiError)
		})
	} finally {
		loading.value = false
	}
}
</script>
