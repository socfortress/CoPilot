<template>
	<n-spin :show="loadingDetails">
		<div class="@container min-h-50">
			<n-alert v-if="detailsError" title="Error" type="error" :description="detailsError" />

			<n-tabs v-else-if="agent" type="line" animated>
				<n-tab-pane name="overview" tab="Overview">
					<AgentOverview :agent @critical-asset-updated="handleCriticalAssetUpdated" />
				</n-tab-pane>
			</n-tabs>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { NAlert, NSpin, NTabPane, NTabs } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import AgentOverview from "./AgentOverview.vue"

const props = defineProps<{
	agentId: string | number | null
}>()

const emit = defineEmits<{
	(e: "criticalAssetUpdated", value: boolean): void
}>()

const agent = ref<Agent | null>(null)
const detailsError = ref<string | null>(null)
const loadingDetails = ref(false)

async function loadAgentDetails() {
	if (props.agentId === null) return

	loadingDetails.value = true
	detailsError.value = null

	try {
		const response = await Api.agents.getAgentById(props.agentId.toString())
		agent.value = response.data.agents?.[0] || null
		if (!agent.value) {
			detailsError.value = "Agent not found."
		}
	} catch (err) {
		detailsError.value = getApiErrorMessage(err as ApiError)
	} finally {
		loadingDetails.value = false
	}
}

function handleCriticalAssetUpdated(payload: boolean) {
	if (!agent.value) return
	agent.value.critical_asset = payload
	emit("criticalAssetUpdated", payload)
}

watch(
	() => props.agentId,
	async newAgentId => {
		agent.value = null
		detailsError.value = null

		if (newAgentId !== null) {
			await loadAgentDetails()
		}
	},
	{ immediate: true }
)
</script>
