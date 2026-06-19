<template>
	<div class="page">
		<div class="flex items-center justify-between">
			<n-button text size="small" :focusable="false" @click="routeAgent().navigate()">
				<template #icon>
					<Icon :name="ArrowIcon" :size="16" />
				</template>
				Back to agents list
			</n-button>
			<n-button v-if="agent" text size="small" :focusable="false" @click.stop="handleDelete">
				<template #icon>
					<Icon :name="DeleteIcon" :size="16" />
				</template>
				Delete Agent
			</n-button>
		</div>

		<CardEntity class="my-4" :highlighted="agent?.critical_asset" :loading="loadingAgent">
			<template #headerMain>
				<div v-if="agent" class="text-default text-xl font-bold">
					{{ agent.hostname }}
				</div>
			</template>
			<template #headerExtra>
				<div class="flex items-center gap-2">
					<n-tag :type="isOnline ? 'success' : 'default'" round class="rounded-lg!" :bordered="false">
						{{ isOnline ? "ONLINE" : "OFFLINE" }}
					</n-tag>

					<n-tooltip v-if="agent">
						<span class="text-sm">Toggle Critical Assets</span>
						<template #trigger>
							<n-button
								:type="agent.critical_asset ? 'error' : 'default'"
								ghost
								size="small"
								@click.stop="toggleCritical(agent.agent_id, agent.critical_asset)"
							>
								<template #icon>
									<Icon :name="agent.critical_asset ? 'carbon:warning-alt' : 'carbon:checkmark'" />
								</template>
								{{ agent.critical_asset ? "Critical Asset" : "Non-Critical Asset" }}
							</n-button>
						</template>
					</n-tooltip>

					<n-tag v-if="agent?.quarantined" type="warning" round class="rounded-lg!" :bordered="false">
						Quarantined
					</n-tag>

					<n-button size="small" :loading="upgradingAgent" @click="upgradeWazuhAgent()">
						Upgrade Wazuh Agent
					</n-button>
				</div>
			</template>
		</CardEntity>

		<n-card content-class="p-4! pt-1!">
			<n-spin :show="loadingAgent">
				<n-tabs type="line" animated default-value="Overview" pane-wrapper-class="min-h-100">
					<n-tab-pane name="Overview" tab="Overview" display-directive="show">
						<OverviewSection v-if="agent" :agent @updated="getAgent()" />
					</n-tab-pane>
					<n-tab-pane name="Vulnerabilities" tab="Vulnerabilities" display-directive="show:lazy">
						<VulnerabilitiesGrid v-if="agent" :agent />
					</n-tab-pane>
					<n-tab-pane name="SCA" tab="SCA" display-directive="show:lazy">
						<ScaTable v-if="agent" :agent />
					</n-tab-pane>
					<n-tab-pane name="Cases" tab="Cases" display-directive="show:lazy">
						<!--
							<AgentCases v-if="agent" :agent />
						-->
						<CasesList v-if="agent" :preset="{ type: 'hostname', value: agent.hostname }" hide-filters />
					</n-tab-pane>
					<n-tab-pane name="Artifacts" tab="Artifacts" display-directive="show:lazy">
						<AgentFlowList v-if="agent" :agent />
					</n-tab-pane>
					<n-tab-pane name="Alerts" tab="Alerts" display-directive="show:lazy">
						<!--
							<AlertsList v-if="agent" :agent-hostname="agent.hostname" />
						-->
						<AlertsList
							v-if="agent"
							:preset="[{ type: 'assetName', value: agent.hostname }]"
							:show-filters="false"
						/>
					</n-tab-pane>
					<n-tab-pane name="collect" tab="Collect" display-directive="show:lazy">
						<ArtifactsCollect
							v-if="agent"
							:hostname="agent.hostname"
							:artifacts
							hide-hostname-field
							@loaded-artifacts="artifacts = $event"
						/>
					</n-tab-pane>
					<n-tab-pane name="command" tab="Command" display-directive="show:lazy">
						<ArtifactsCommand
							v-if="agent"
							:hostname="agent.hostname"
							:artifacts
							hide-hostname-field
							@loaded-artifacts="artifacts = $event"
						/>
					</n-tab-pane>
					<n-tab-pane name="quarantine" tab="Quarantine" display-directive="show:lazy">
						<ArtifactsQuarantine
							v-if="agent"
							:hostname="agent.hostname"
							:artifacts
							hide-hostname-field
							@action-performed="getAgent()"
							@loaded-artifacts="artifacts = $event"
						/>
					</n-tab-pane>
					<n-tab-pane name="active-response" tab="Active Response" display-directive="show:lazy">
						<ActiveResponseAgent v-if="agent" :agent embedded />
					</n-tab-pane>
					<n-tab-pane name="file-collection" tab="File Collection" display-directive="show:lazy">
						<div class="section">
							<FileCollectionForm v-if="agent" :agent-id="agent.agent_id" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="data-store" tab="Data Store" display-directive="show:lazy">
						<div class="section">
							<AgentDataStore v-if="agent" :agent-id="agent.agent_id" />
						</div>
					</n-tab-pane>
				</n-tabs>
			</n-spin>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents"
import type { Artifact } from "@/types/artifacts"
import type { ApiError } from "@/types/common"
import { NButton, NCard, NSpin, NTabPane, NTabs, NTag, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, nextTick, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import { handleDeleteAgent, toggleAgentCritical } from "@/components/agents/utils"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { AgentStatus } from "@/types/agents"
import { getApiErrorMessage } from "@/utils"

const VulnerabilitiesGrid = defineAsyncComponent(
	() => import("@/components/agents/vulnerabilities/VulnerabilitiesGrid.vue")
)
const ScaTable = defineAsyncComponent(() => import("@/components/agents/sca/ScaTable.vue"))
// const AlertsList = defineAsyncComponent(() => import("@/components/alerts/AlertsList.vue"))
const AlertsList = defineAsyncComponent(() => import("@/components/incidentManagement/alerts/AlertsList.vue"))
const OverviewSection = defineAsyncComponent(() => import("@/components/agents/OverviewSection.vue"))
// const AgentCases = defineAsyncComponent(() => import("@/components/agents/AgentCases.vue"))
const CasesList = defineAsyncComponent(() => import("@/components/incidentManagement/cases/CasesList.vue"))
const AgentFlowList = defineAsyncComponent(() => import("@/components/agents/agentFlow/AgentFlowList.vue"))
const ArtifactsCollect = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCollect.vue"))
const ArtifactsCommand = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCommand.vue"))
const ArtifactsQuarantine = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsQuarantine.vue"))
const ActiveResponseAgent = defineAsyncComponent(() => import("@/components/activeResponse/ActiveResponseAgent.vue"))
const AgentDataStore = defineAsyncComponent(() => import("@/components/agents/dataStore/AgentDataStore.vue"))
const FileCollectionForm = defineAsyncComponent(
	() => import("@/components/agents/fileCollection/FileCollectionForm.vue")
)

const ArrowIcon = "carbon:arrow-left"
const DeleteIcon = "ph:trash"

const { routeAgent } = useNavigation()
const message = useMessage()
const router = useRouter()
const dialog = useDialog()
const route = useRoute()
const loadingAgent = ref(false)
const upgradingAgent = ref(false)
const agent = ref<Agent | null>(null)
const agentId = ref<string | null>(null)

const artifacts = ref<Artifact[]>([])

const isOnline = computed(() => {
	return agent.value?.wazuh_agent_status === AgentStatus.Active
})

function getAgent() {
	if (agentId.value) {
		loadingAgent.value = true

		Api.agents
			.getAgents(agentId.value)
			.then(res => {
				if (res.data.success) {
					agent.value = res.data.agents[0] || null
				} else {
					message.error(res.data?.message || "An error occurred. Please try again later.")
					routeAgent().navigate()
				}
			})
			.catch(err => {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
				routeAgent().navigate()
			})
			.finally(() => {
				loadingAgent.value = false
			})
	}
}

function upgradeWazuhAgent() {
	if (agentId.value) {
		upgradingAgent.value = true

		Api.agents
			.upgradeWazuhAgent(agentId.value)
			.then(res => {
				if (res.data.success) {
					message.success(res.data?.message || "Agent upgraded successfully")
				} else {
					message.error(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			})
			.finally(() => {
				upgradingAgent.value = false
			})
	}
}

function toggleCritical(agentId: string, criticalStatus: boolean) {
	toggleAgentCritical({
		agentId,
		criticalStatus,
		message,
		cbBefore: () => {
			loadingAgent.value = true
		},
		cbSuccess: () => {
			if (agent.value?.critical_asset !== undefined) {
				agent.value.critical_asset = !criticalStatus
			}
		},
		cbAfter: () => {
			loadingAgent.value = false
		}
	})
}

function handleDelete() {
	if (agent.value) {
		handleDeleteAgent({
			agent: agent.value,
			message,
			dialog,
			cbBefore: () => {
				loadingAgent.value = true
			},
			cbSuccess: () => {
				routeAgent().navigate()
			},
			cbAfter: () => {
				loadingAgent.value = false
			}
		})
	}
}

onBeforeMount(() => {
	if (route.params.id) {
		agentId.value = route.params.id.toString()

		nextTick(() => {
			getAgent()
		})
	} else {
		router.replace({ name: "Agents" }).catch(() => {})
	}
})
</script>
