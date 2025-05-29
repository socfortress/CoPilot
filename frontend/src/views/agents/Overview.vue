<template>
	<div class="page">
		<div class="agent-toolbar">
			<div class="back-btn" @click="gotoAgent()">
				<Icon :name="ArrowIcon" :size="16"></Icon>
				<span>Agents list</span>
			</div>
			<div v-if="agent" class="delete-btn" @click.stop="handleDelete">Delete Agent</div>
		</div>
		<CardEntity
			class="agent-header my-4"
			:class="{ critical: agent?.critical_asset, online: isOnline }"
			:loading="loadingAgent"
		>
			<div class="flex flex-wrap items-start justify-between gap-x-6 gap-y-1">
				<div class="info grow">
					<div class="title">
						<div v-if="agent" class="critical" :class="{ active: agent?.critical_asset }">
							<n-tooltip>
								Toggle Critical Assets
								<template #trigger>
									<n-button
										text
										:type="agent?.critical_asset ? 'warning' : 'default'"
										circle
										@click.stop="toggleCritical(agent.agent_id, agent.critical_asset)"
									>
										<template #icon>
											<Icon :name="StarIcon"></Icon>
										</template>
									</n-button>
								</template>
							</n-tooltip>
						</div>

						<h1 v-if="agent?.hostname">
							{{ agent?.hostname }}
						</h1>

						<n-tag v-if="isOnline" type="success" round :bordered="false">ONLINE</n-tag>
						<n-tag v-if="isQuarantined" type="warning" round :bordered="false">
							<template #icon>
								<Icon :name="QuarantinedIcon"></Icon>
							</template>
							<span>QUARANTINED</span>
						</n-tag>
					</div>
					<div class="label text-secondary mt-2">Agent #{{ agent?.agent_id }}</div>
				</div>
				<div class="actions flex grow items-center justify-end">
					<n-button size="small" ghost type="primary" :loading="upgradingAgent" @click="upgradeWazuhAgent()">
						Upgrade Wazuh Agent
					</n-button>
				</div>
			</div>
		</CardEntity>
		<n-card class="px-4 py-1 pb-4" content-style="padding:0">
			<n-spin :show="loadingAgent">
				<n-tabs type="line" animated default-value="Overview">
					<n-tab-pane name="Overview" tab="Overview" display-directive="show">
						<div class="section">
							<OverviewSection v-if="agent" :agent @updated="getAgent()" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Vulnerabilities" tab="Vulnerabilities" display-directive="show:lazy">
						<div class="section">
							<VulnerabilitiesGrid v-if="agent" :agent />
						</div>
					</n-tab-pane>
					<n-tab-pane name="SCA" tab="SCA" display-directive="show:lazy">
						<div class="section">
							<ScaTable v-if="agent" :agent />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Cases" tab="Cases" display-directive="show:lazy">
						<div class="section">
							<!--
								<AgentCases v-if="agent" :agent />
							-->
							<CasesList
								v-if="agent"
								class="px-1"
								:preset="{ type: 'hostname', value: agent.hostname }"
								hide-filters
							/>
						</div>
					</n-tab-pane>
					<n-tab-pane name="Artifacts" tab="Artifacts" display-directive="show:lazy">
						<div class="section">
							<AgentFlowList v-if="agent" :agent />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Alerts" tab="Alerts" display-directive="show:lazy">
						<div class="section">
							<!--
								<AlertsList v-if="agent" :agent-hostname="agent.hostname" />
							-->
							<AlertsList
								v-if="agent"
								class="px-1"
								:preset="[{ type: 'assetName', value: agent.hostname }]"
								:show-filters="false"
							/>
						</div>
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
						<ActiveResponseAgent v-if="agent" :agent="agent" embedded />
					</n-tab-pane>
				</n-tabs>
			</n-spin>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import type { Artifact } from "@/types/artifacts.d"
import { NButton, NCard, NSpin, NTabPane, NTabs, NTag, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, nextTick, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import { handleDeleteAgent, toggleAgentCritical } from "@/components/agents/utils"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { AgentStatus } from "@/types/agents.d"

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

const StarIcon = "carbon:star"
const QuarantinedIcon = "ph:seal-warning-light"
const ArrowIcon = "carbon:arrow-left"

const { gotoAgent } = useGoto()
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

const isQuarantined = computed(() => {
	return !!agent.value?.quarantined
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
					gotoAgent()
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				gotoAgent()
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
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
				gotoAgent()
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

<style lang="scss" scoped>
.page {
	.agent-toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;

		.back-btn {
			cursor: pointer;
			opacity: 0.8;
			font-size: 14px;

			i {
				font-size: 20px;
			}

			span {
				position: relative;
				top: -3px;
				margin-left: 4px;
			}
		}

		.delete-btn {
			opacity: 0.8;
			cursor: pointer;
			font-size: 14px;
		}
	}

	.agent-header {
		.title {
			display: flex;
			align-items: center;
			line-height: 1;
			gap: calc(var(--spacing) * 4);

			h1 {
				margin: 0;
				font-size: var(--text-2xl);
				word-break: break-all;
			}

			.critical {
				display: flex;
				align-items: center;
			}
		}

		&.critical {
			border-color: var(--warning-color);
		}
	}

	.section {
		margin-top: calc(var(--spacing) * 2);
		min-height: 200px;
	}
}
</style>
