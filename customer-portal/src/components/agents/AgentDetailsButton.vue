<template>
	<EntityDetailsButton
		title="Agent Details"
		entity="agent"
		:route="routeAgentDetails(agentId.toString())"
		:size
		:ghost
	>
		<AgentDetails :agent-id @critical-asset-updated="emit('criticalAssetUpdated', $event)" />
	</EntityDetailsButton>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { AgentCriticalUpdateSuccessPayload } from "./AgentCriticalSelect.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import AgentDetails from "./AgentDetails/AgentDetails.vue"

defineProps<{
	agentId: string | number
	size?: ButtonSize
	/** Transparent background, for buttons sitting on a surface that already has one. */
	ghost?: boolean
}>()

const emit = defineEmits<{
	(e: "criticalAssetUpdated", value: AgentCriticalUpdateSuccessPayload): void
}>()

const { routeAgentDetails } = useNavigation()
</script>
