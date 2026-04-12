<template>
	<div>
		<n-button @click="showDetails = true">View Details</n-button>

		<n-modal
			v-model:show="showDetails"
			title="Case Details"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
		>
			<CaseDetails
				:case-id
				@assigned-to-updated="handleAssignedToUpdated"
				@status-updated="handleStatusUpdated"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CaseAssignedUpdateSuccessPayload } from "./CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "./CaseStatusSelect.vue"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import CaseDetails from "./CaseDetails"

defineProps<{
	caseId: number | null
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: CaseStatusUpdateSuccessPayload): void
	(e: "assignedToUpdated", value: CaseAssignedUpdateSuccessPayload): void
}>()

const showDetails = ref(false)

function handleStatusUpdated(payload: CaseStatusUpdateSuccessPayload) {
	emit("statusUpdated", payload)
}

function handleAssignedToUpdated(payload: CaseAssignedUpdateSuccessPayload) {
	emit("assignedToUpdated", payload)
}
</script>
