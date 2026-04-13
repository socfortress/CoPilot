<template>
	<div>
		<n-button-group :size>
			<n-button :focusable="false" @click="showDetails = true">
				<template #icon>
					<Icon name="carbon:view" />
				</template>
				View Details
			</n-button>
			<n-button :focusable="false" @click="routeCaseDetails(caseId).navigate()">
				<template #icon>
					<Icon name="carbon:launch" />
				</template>
			</n-button>
		</n-button-group>

		<n-modal
			v-model:show="showDetails"
			title="Case Details"
			preset="card"
			display-directive="show"
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
import type { ButtonSize } from "naive-ui"
import type { CaseAssignedUpdateSuccessPayload } from "./CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "./CaseStatusSelect.vue"
import { NButton, NButtonGroup, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import CaseDetails from "./CaseDetails"

defineProps<{
	caseId: number
	size?: ButtonSize
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: CaseStatusUpdateSuccessPayload): void
	(e: "assignedToUpdated", value: CaseAssignedUpdateSuccessPayload): void
}>()

const { routeCaseDetails } = useNavigation()
const showDetails = ref(false)

function handleStatusUpdated(payload: CaseStatusUpdateSuccessPayload) {
	emit("statusUpdated", payload)
}

function handleAssignedToUpdated(payload: CaseAssignedUpdateSuccessPayload) {
	emit("assignedToUpdated", payload)
}
</script>
