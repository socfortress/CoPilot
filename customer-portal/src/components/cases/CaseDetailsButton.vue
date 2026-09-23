<template>
	<EntityDetailsButton
		v-slot="{ close }"
		title="Case Details"
		entity="case"
		:route="routeCaseDetails(caseId)"
		:size
		:ghost
	>
		<CaseDetails
			:case-id
			@status-updated="emit('statusUpdated', $event)"
			@assigned-to-updated="emit('assignedToUpdated', $event)"
			@deleted="handleDeleted(close)"
		/>
	</EntityDetailsButton>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { CaseAssignedUpdateSuccessPayload } from "./CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "./CaseStatusSelect.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import CaseDetails from "./CaseDetails"

defineProps<{
	caseId: number
	size?: ButtonSize
	/** Transparent background, for buttons sitting on a surface that already has one. */
	ghost?: boolean
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: CaseStatusUpdateSuccessPayload): void
	(e: "assignedToUpdated", value: CaseAssignedUpdateSuccessPayload): void
	(e: "deleted"): void
}>()

const { routeCaseDetails } = useNavigation()

/** A deleted case has nothing left to show: close the modal before telling the list. */
function handleDeleted(close: () => void) {
	close()
	emit("deleted")
}
</script>
