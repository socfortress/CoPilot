<template>
	<div>
		<n-button-group :size>
			<n-button :focusable="false" :ghost @click="showDetails = true">
				<template #icon>
					<Icon name="carbon:view" />
				</template>
				View Details
			</n-button>
			<n-button :focusable="false" :ghost @click="routeAlertDetails(alertId).navigate()">
				<template #icon>
					<Icon name="carbon:launch" />
				</template>
			</n-button>
		</n-button-group>

		<n-modal
			v-model:show="showDetails"
			title="Alert Details"
			preset="card"
			display-directive="show"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
		>
			<AlertDetails :alert-id @status-updated="handleStatusUpdated" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { AlertStatusUpdateSuccessPayload } from "./AlertStatusSelect.vue"
import { NButton, NButtonGroup, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
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
const showDetails = ref(false)

function handleStatusUpdated(payload: AlertStatusUpdateSuccessPayload) {
	emit("statusUpdated", payload)
}
</script>
