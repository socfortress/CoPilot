<template>
	<n-select
		to="body"
		:value="selectedStatus"
		:options="statusOptions"
		:loading
		size="small"
		class="min-w-36"
		:disabled="readOnly"
		:title="readOnly ? $t('common.readOnly.hint') : undefined"
		:consistent-menu-width="false"
		@update:value="handleStatusChange"
	/>
</template>

<script setup lang="ts">
import type { CaseStatus } from "@/types/cases"
import type { ApiError } from "@/types/common"
import { NSelect, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import { useReadOnly } from "@/composables/common/useReadOnly"
import { getApiErrorMessage } from "@/utils"
import { statusSelectOptions, workflowStatusLabel } from "@/utils/workflowStatus"

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
	/** Its customer: read-only there, the select is disabled (#1312). */
	customerCode?: string | null
}>()

const emit = defineEmits<{
	success: [payload: CaseStatusUpdateSuccessPayload]
	error: [payload: CaseStatusUpdateErrorPayload]
}>()

const readOnly = useReadOnly(() => props.customerCode)

const message = useMessage()
const { t } = useI18n()

const selectedStatus = ref<CaseStatus>(props.status)
// The waiting status is shown while the item is in it, never offered (see workflowStatus.ts).
const statusOptions = computed(() => statusSelectOptions(selectedStatus.value))
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
		message.success(t("cases.caseStatusSelect.updated", { status: workflowStatusLabel(selectedStatus.value) }))
		emit("success", {
			caseId: props.caseId,
			status: selectedStatus.value
		})
	} catch (err) {
		selectedStatus.value = previousStatus
		message.error(getApiErrorMessage(err as ApiError))
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
