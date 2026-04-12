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
import type { CaseStatus } from "@/types/cases"
import type { ApiError } from "@/types/common"
import { NSelect } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface CaseStatusUpdateSuccessPayload {
	caseId: number
	status: CaseStatus
}

export interface CaseStatusUpdateErrorPayload {
	caseId: number
	status: CaseStatus
	message: string
}

const props = defineProps<{
	caseId: number
	status: CaseStatus
}>()

const emit = defineEmits<{
	success: [payload: CaseStatusUpdateSuccessPayload]
	error: [payload: CaseStatusUpdateErrorPayload]
}>()

const statusOptions = [
	{ label: "Open", value: "OPEN" },
	{ label: "In Progress", value: "IN_PROGRESS" },
	{ label: "Closed", value: "CLOSED" }
]

const selectedStatus = ref<CaseStatus>(props.status)
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
	selectedStatus.value = value as CaseStatus
	loading.value = true

	try {
		await Api.cases.updateCaseStatus(props.caseId, selectedStatus.value)
		emit("success", {
			caseId: props.caseId,
			status: selectedStatus.value
		})
	} catch (err) {
		selectedStatus.value = previousStatus
		emit("error", {
			caseId: props.caseId,
			status: previousStatus,
			message: getApiErrorMessage(err as ApiError)
		})
	} finally {
		loading.value = false
	}
}
</script>
