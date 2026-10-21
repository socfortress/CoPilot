<template>
	<n-spin :show="loadingDetails">
		<div class="@container min-h-50">
			<n-alert v-if="detailsError" title="Error" type="error" :description="detailsError" />
			<!-- What the backend already served to customers, now in tabs (#1256); each loads when first opened. -->
			<n-tabs v-else-if="agent" v-model:value="activeTab" type="line" animated data-testid="agent-tabs">
				<n-tab-pane name="overview" tab="Overview">
					<AgentOverview :agent @critical-asset-updated="handleCriticalAssetUpdated" />
				</n-tab-pane>
				<n-tab-pane name="vulnerabilities" tab="Vulnerabilities" display-directive="show:lazy">
					<AgentVulnerabilities :agent-id="agent.agent_id" :agent-label="agent.hostname" :initial-search />
				</n-tab-pane>
				<n-tab-pane name="sca" tab="SCA" display-directive="show:lazy">
					<AgentSca :agent-id="agent.agent_id" :agent-label="agent.hostname" :initial-policy />
				</n-tab-pane>
				<n-tab-pane name="cases" tab="Cases" display-directive="show:lazy">
					<AgentCases :hostname="agent.hostname" />
				</n-tab-pane>
			</n-tabs>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AgentCriticalUpdateSuccessPayload } from "../AgentCriticalSelect.vue"
import type { Agent } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { NAlert, NSpin, NTabPane, NTabs } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import AgentCases from "./AgentCases.vue"
import AgentOverview from "./AgentOverview.vue"
import AgentSca from "./AgentSca.vue"
import AgentVulnerabilities from "./AgentVulnerabilities.vue"

const props = defineProps<{
	agentId: string | number | null
	/** Opens this tab first: `vulnerabilities`, `sca` or `cases` (the Exposure page links them, #1289). */
	initialTab?: string
	/** The Vulnerabilities tab's search, prefilled. */
	initialSearch?: string
	/** The SCA policy to open. */
	initialPolicy?: string
}>()

const emit = defineEmits<{
	(e: "criticalAssetUpdated", value: AgentCriticalUpdateSuccessPayload): void
}>()
const TABS = ["overview", "vulnerabilities", "sca", "cases"]
const firstTab = () => (props.initialTab && TABS.includes(props.initialTab) ? props.initialTab : "overview")

const agent = ref<Agent | null>(null)
const activeTab = ref(firstTab())
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

function handleCriticalAssetUpdated(payload: AgentCriticalUpdateSuccessPayload) {
	if (!agent.value) return
	agent.value.critical_asset = payload.critical
	emit("criticalAssetUpdated", payload)
}

watch(
	() => props.agentId,
	async newAgentId => {
		agent.value = null
		activeTab.value = firstTab()
		detailsError.value = null

		if (newAgentId !== null) {
			await loadAgentDetails()
		}
	},
	{ immediate: true }
)
</script>
