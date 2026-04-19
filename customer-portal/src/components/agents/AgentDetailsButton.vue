<template>
	<div>
		<n-button-group :size>
			<n-button :focusable="false" @click="showDetails = true">
				<template #icon>
					<Icon name="carbon:view" />
				</template>
				View Details
			</n-button>
			<n-button :focusable="false" @click="routeAgentDetails(agentId.toString()).navigate()">
				<template #icon>
					<Icon name="carbon:launch" />
				</template>
			</n-button>
		</n-button-group>

		<n-modal
			v-model:show="showDetails"
			title="Agent Details"
			preset="card"
			display-directive="show"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
		>
			<AgentDetails :agent-id @critical-asset-updated="handleCriticalAssetUpdated" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { AgentCriticalUpdateSuccessPayload } from "./AgentCriticalSelect.vue"
import { NButton, NButtonGroup, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import AgentDetails from "./AgentDetails/AgentDetails.vue"

defineProps<{
	agentId: string | number
	size?: ButtonSize
}>()

const emit = defineEmits<{
	(e: "criticalAssetUpdated", value: AgentCriticalUpdateSuccessPayload): void
}>()

const { routeAgentDetails } = useNavigation()
const showDetails = ref(false)

function handleCriticalAssetUpdated(payload: AgentCriticalUpdateSuccessPayload) {
	emit("criticalAssetUpdated", payload)
}
</script>
