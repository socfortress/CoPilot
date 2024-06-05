<template>
	<div class="page">
		<div class="agent-toolbar">
			<div class="back-btn" @click="gotoAgent()">
				<Icon :name="ArrowIcon" :size="16"></Icon>
				<span>Agents list</span>
			</div>
			<div class="delete-btn" @click.stop="handleDelete" v-if="agent">Delete Agent</div>
		</div>
		<n-spin
			class="agent-header py-5 px-7 my-4"
			content-class="flex justify-between gap-y-1 gap-x-6 flex-wrap items-start"
			:class="{ critical: agent?.critical_asset, online: isOnline }"
			:show="loadingAgent"
		>
			<div class="info grow">
				<div class="title">
					<div class="critical" :class="{ active: agent?.critical_asset }" v-if="agent">
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

					<span class="online-badge" v-if="isOnline">ONLINE</span>

					<span class="quarantined-badge flex items-center gap-1" v-if="isQuarantined">
						<Icon :name="QuarantinedIcon" :size="15"></Icon>
						<span>QUARANTINED</span>
					</span>
				</div>
				<div class="label text-secondary-color mt-2">Agent #{{ agent?.agent_id }}</div>
			</div>
			<div class="actions flex items-center justify-end grow">
				<n-button size="small" ghost type="primary" :loading="upgradingAgent" @click="upgradeWazuhAgent()">
					Upgrade Wazuh Agent
				</n-button>
			</div>
		</n-spin>
		<n-card class="py-1 px-4 pb-4" content-style="padding:0">
			<n-spin :show="loadingAgent">
				<n-tabs type="line" animated default-value="Overview">
					<n-tab-pane name="Overview" tab="Overview" display-directive="show">
						<div class="section">
							<OverviewSection v-if="agent" :agent="agent" @updated="getAgent()" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Vulnerabilities" tab="Vulnerabilities" display-directive="show:lazy">
						<div class="section">
							<VulnerabilitiesGrid v-if="agent" :agent="agent" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="SCA" tab="SCA" display-directive="show:lazy">
						<div class="section">
							<ScaTable v-if="agent" :agent="agent" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Cases" tab="Cases" display-directive="show:lazy">
						<div class="section">
							<AgentCases v-if="agent" :agent="agent" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Artifacts" tab="Artifacts" display-directive="show:lazy">
						<div class="section">
							<AgentFlowList v-if="agent" :agent="agent" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Alerts" tab="Alerts" display-directive="show:lazy">
						<div class="section">
							<AlertsList v-if="agent" :agent-hostname="agent.hostname" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="collect" tab="Collect" display-directive="show:lazy">
						<ArtifactsCollect
							v-if="agent"
							@loaded-artifacts="artifacts = $event"
							:hostname="agent.hostname"
							:artifacts
							hide-hostname-field
						/>
					</n-tab-pane>
					<n-tab-pane name="command" tab="Command" display-directive="show:lazy">
						<ArtifactsCommand
							v-if="agent"
							@loaded-artifacts="artifacts = $event"
							:hostname="agent.hostname"
							:artifacts
							hide-hostname-field
						/>
					</n-tab-pane>
					<n-tab-pane name="quarantine" tab="Quarantine" display-directive="show:lazy">
						<ArtifactsQuarantine
							v-if="agent"
							@action-performed="getAgent()"
							@loaded-artifacts="artifacts = $event"
							:hostname="agent.hostname"
							:artifacts
							hide-hostname-field
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
import { ref, onBeforeMount, computed, nextTick } from "vue"
import { useMessage, NSpin, NTooltip, NButton, NTabs, NTabPane, NCard, useDialog } from "naive-ui"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import { AgentStatus, type Agent } from "@/types/agents.d"
import { handleDeleteAgent, toggleAgentCritical } from "@/components/agents/utils"
import VulnerabilitiesGrid from "@/components/agents/vulnerabilities/VulnerabilitiesGrid.vue"
import ScaTable from "@/components/agents/sca/ScaTable.vue"
import AlertsList from "@/components/alerts/AlertsList.vue"
import OverviewSection from "@/components/agents/OverviewSection.vue"
import AgentCases from "@/components/agents/AgentCases.vue"
import AgentFlowList from "@/components/agents/agentFlow/AgentFlowList.vue"
import Icon from "@/components/common/Icon.vue"
import type { Artifact } from "@/types/artifacts.d"
import ArtifactsCollect from "@/components/artifacts/ArtifactsCollect.vue"
import ArtifactsCommand from "@/components/artifacts/ArtifactsCommand.vue"
import ArtifactsQuarantine from "@/components/artifacts/ArtifactsQuarantine.vue"
import ActiveResponseAgent from "@/components/activeResponse/ActiveResponseAgent.vue"
import { useGoto } from "@/composables/useGoto"

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
		border: 2px solid transparent;
		border-radius: var(--border-radius);
		background-color: var(--bg-color);

		.title {
			display: flex;
			align-items: center;
			line-height: 1;
			@apply gap-4;

			h1 {
				margin: 0;
				@apply text-2xl;
				word-break: break-all;
			}

			.critical {
				display: flex;
				align-items: center;
			}
			.online-badge,
			.quarantined-badge {
				border: 2px solid var(--success-color);
				color: var(--success-color);
				font-weight: bold;
				border-radius: var(--border-radius);
				@apply text-xs py-1 px-2;
			}

			.quarantined-badge {
				border-color: var(--warning-color);
				color: var(--warning-color);
			}
		}

		&.critical {
			border-color: var(--warning-color);
		}
	}

	.section {
		min-height: 200px;
		@apply mt-2;
	}
}
</style>
