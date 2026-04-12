<template>
	<div>
		<n-button @click="showDetails = true">View Details</n-button>

		<n-modal
			v-model:show="showDetails"
			title="Alert Details"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
		>
			<AlertDetails :alert-id @status-updated="handleStatusUpdated" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AlertStatusUpdateSuccessPayload } from "./AlertStatusSelect.vue"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import AlertDetails from "./AlertDetails"

defineProps<{
	alertId: number | null
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: AlertStatusUpdateSuccessPayload): void
}>()

const showDetails = ref(false)

function handleStatusUpdated(payload: AlertStatusUpdateSuccessPayload) {
	emit("statusUpdated", payload)
}
</script>
