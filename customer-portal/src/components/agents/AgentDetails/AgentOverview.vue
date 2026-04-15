<template>
	<EntityDetailsCard :fields>
		<template #suffix>
			<CardKV label="wazuh_agent_status">
				<Chip
					:type="getStatusColor(agent.wazuh_agent_status)"
					:value="agent.wazuh_agent_status.toUpperCase()"
				/>
			</CardKV>

			<CardKV label="critical_asset">
				<AgentCriticalSelect
					:agent-id="agent.agent_id"
					:critical="agent.critical_asset"
					@success="handleCriticalAssetUpdateSuccess"
				/>
			</CardKV>
		</template>
	</EntityDetailsCard>
</template>

<script setup lang="ts">
import type { AgentCriticalUpdateSuccessPayload } from "../AgentCriticalSelect.vue"
import type { Field } from "@/components/common/entity/EntityDetailsCard.vue"
import type { Agent } from "@/types/agents"
import _omit from "lodash/omit"
import { computed } from "vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Chip from "@/components/common/Chip.vue"
import EntityDetailsCard from "@/components/common/entity/EntityDetailsCard.vue"
import { getStatusColor } from "@/utils"
import AgentCriticalSelect from "../AgentCriticalSelect.vue"

const props = defineProps<{
	agent: Agent
}>()

const emit = defineEmits<{
	(e: "criticalAssetUpdated", value: AgentCriticalUpdateSuccessPayload): void
}>()

const fields = computed<Field[]>(() =>
	Object.entries(_omit(props.agent, ["critical_asset", "wazuh_agent_status"])).map(([key, value]) => ({
		label: key,
		value
	}))
)

function handleCriticalAssetUpdateSuccess(payload: AgentCriticalUpdateSuccessPayload) {
	emit("criticalAssetUpdated", payload)
}
</script>
