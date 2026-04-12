<template>
	<n-select
		:value="selectedAssignedTo"
		:options="assignedToOptions"
		:loading
		size="small"
		class="min-w-36"
		@update:value="handleAssignedToChange"
	/>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NSelect, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface CaseAssignedUpdateSuccessPayload {
	caseId: number
	assignedTo: string
}

export interface CaseAssignedUpdateErrorPayload {
	caseId: number
	assignedTo: string | null
	message: string
}

const props = defineProps<{
	caseId: number
	assignedTo: string | null
	assignedAvailable?: string[]
}>()

const emit = defineEmits<{
	success: [payload: CaseAssignedUpdateSuccessPayload]
	error: [payload: CaseAssignedUpdateErrorPayload]
}>()

const message = useMessage()

const assignedToOptions = ref<{ label: string; value: string }[]>([])

const selectedAssignedTo = ref<string | null>(props.assignedTo)
const loading = ref(false)

watch(
	() => props.assignedTo,
	newAssignedTo => {
		selectedAssignedTo.value = newAssignedTo
	}
)

async function handleAssignedToChange(value: string) {
	if (loading.value || value === selectedAssignedTo.value) return

	const previousAssignedTo = selectedAssignedTo.value
	selectedAssignedTo.value = value
	loading.value = true

	try {
		await Api.cases.updateCaseAssignedTo(props.caseId, selectedAssignedTo.value)
		message.success(`Assigned to updated to ${selectedAssignedTo.value}`)
		emit("success", {
			caseId: props.caseId,
			assignedTo: selectedAssignedTo.value
		})
	} catch (err) {
		selectedAssignedTo.value = previousAssignedTo
		message.error(getApiErrorMessage(err as ApiError))
		emit("error", {
			caseId: props.caseId,
			assignedTo: previousAssignedTo,
			message: getApiErrorMessage(err as ApiError)
		})
	} finally {
		loading.value = false
	}
}

async function loadAssignedToOptions() {
	const response = await Api.cases.getCasesFilters()
	assignedToOptions.value = response.data.assigned_to.map(o => ({ label: o, value: o }))
}

onBeforeMount(() => {
	if (props.assignedAvailable?.length) {
		assignedToOptions.value = props.assignedAvailable.map(o => ({ label: o, value: o }))
	} else {
		loadAssignedToOptions()
	}
})
</script>
