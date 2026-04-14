<template>
	<div v-if="alert.linked_cases?.length" class="flex flex-col gap-2">
		<CardEntity v-for="linkedCase in alert.linked_cases" :key="linkedCase.id" size="small" embedded>
			<template #header-main>#{{ linkedCase.id }}</template>
			<template #header-extra>
				<Chip :type="getStatusColor(linkedCase.case_status)">
					{{ linkedCase.case_status.replace("_", " ").toUpperCase() }}
				</Chip>
			</template>
			<template #default>
				{{ linkedCase.case_name }}
			</template>
			<template #footer-main>
				Created: {{ formatDate(linkedCase.case_creation_time, dFormats.datetime) }}
			</template>
			<template #footer-extra>
				<div class="flex flex-wrap items-center justify-end gap-2">
					<Chip v-if="linkedCase.assigned_to" :value="linkedCase.assigned_to" label="Assigned to" />
					<UnlinkCase
						:alert-id="alert.id"
						:case-id="linkedCase.id"
						size="small"
						@unlinked="handleCaseUnlinked"
					/>
					<CaseDetailsButton
						:case-id="linkedCase.id"
						size="small"
						@status-updated="handleStatusUpdated"
						@assigned-to-updated="handleAssignedToUpdated"
					/>
				</div>
			</template>
		</CardEntity>
	</div>

	<div v-else-if="alert.case_ids?.length" class="flex flex-wrap gap-2">
		<code v-for="caseId in alert.case_ids" :key="caseId">Case #{{ caseId }}</code>
	</div>

	<n-empty v-else description="No linked cases found" class="min-h-50 justify-center">
		<template #extra>
			<n-button type="primary" size="small" :loading="creatingCase" @click="createCase">Create Case</n-button>
		</template>
	</n-empty>
</template>

<script setup lang="ts">
import type { CaseAssignedUpdateSuccessPayload } from "@/components/cases/CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "@/components/cases/CaseStatusSelect.vue"
import type { Alert } from "@/types/alerts"
import type { ApiError } from "@/types/common"
import { NButton, NEmpty, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import CaseDetailsButton from "@/components/cases/CaseDetailsButton.vue"
import UnlinkCase from "@/components/cases/UnlinkCase.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"

const { alert } = defineProps<{
	alert: Alert
}>()

const emit = defineEmits<{
	(e: "created", value: number): void
	(e: "updated", value: number): void
	(e: "unlinked", value: number): void
}>()

const dFormats = useSettingsStore().dateFormat
const creatingCase = ref(false)
const message = useMessage()

function createCase() {
	creatingCase.value = true

	Api.cases
		.createCaseFromAlert(alert.id)
		.then(res => {
			if (res.data.success) {
				emit("created", res.data.case_alert_link.case_id)
				message.success(res.data?.message || "Case created successfully")
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError))
		})
		.finally(() => {
			creatingCase.value = false
		})
}

function handleStatusUpdated(payload: CaseStatusUpdateSuccessPayload) {
	emit("updated", payload.caseId)
}

function handleAssignedToUpdated(payload: CaseAssignedUpdateSuccessPayload) {
	emit("updated", payload.caseId)
}

function handleCaseUnlinked(caseId: number) {
	emit("unlinked", caseId)
}
</script>
