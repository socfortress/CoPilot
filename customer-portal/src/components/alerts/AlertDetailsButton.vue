<template>
	<EntityDetailsButton title="Alert Details" entity="alert" :route="routeAlertDetails(alertId)" :size :ghost>
		<AlertDetails :alert-id @status-updated="emit('statusUpdated', $event)" />
	</EntityDetailsButton>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { AlertStatusUpdateSuccessPayload } from "./AlertStatusSelect.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import AlertDetails from "./AlertDetails"

defineProps<{
	alertId: number
	size?: ButtonSize
	/** Transparent background, for buttons sitting on a surface that already has one. */
	ghost?: boolean
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: AlertStatusUpdateSuccessPayload): void
}>()

const { routeAlertDetails } = useNavigation()
</script>
