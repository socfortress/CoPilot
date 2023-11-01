<template>
	<div class="page">
		<div class="agent-toolbar">
			<div class="back-btn" @click="gotoAgents()">
				<Icon :name="ArrowIcon" :size="16"></Icon>
				<span>Agents list</span>
			</div>
			<div class="delete-btn" @click.stop="handleDelete" v-if="agent">Delete Agent</div>
		</div>
		<n-spin
			class="agent-header py-5 px-7 my-4"
			:class="{ critical: agent?.critical_asset, online: isOnline }"
			:show="loadingAgent"
		>
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
			</div>
			<div class="label opacity-60 mt-2">Agent #{{ agent?.agent_id }}</div>
		</n-spin>
		<n-card class="p-2" content-style="padding:0">
			<n-spin :show="loadingAgent">
				<n-tabs type="segment" animated default-value="Overview">
					<n-tab-pane name="Overview" tab="Overview" display-directive="show">
						<div class="section">
							<OverviewSection v-if="agent" :agent="agent" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Vulnerabilities" tab="Vulnerabilities" display-directive="show">
						<div class="section">
							<VulnerabilitiesSection v-if="agent" :agent="agent" />
						</div>
					</n-tab-pane>
					<n-tab-pane name="Alerts" tab="Alerts" display-directive="show">
						<div class="section">...yet to be implemented...</div>
					</n-tab-pane>
				</n-tabs>
			</n-spin>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import { type Agent } from "@/types/agents.d"
import { handleDeleteAgent, isAgentOnline, toggleAgentCritical } from "@/components/agents/utils"
import { useRouter } from "vue-router"
import VulnerabilitiesSection from "@/components/agents/VulnerabilitiesSection.vue"
import OverviewSection from "@/components/agents/OverviewSection.vue"
import { useMessage, NSpin, NTooltip, NButton, NTabs, NTabPane, NCard, useDialog } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const StarIcon = "carbon:star"
const ArrowIcon = "carbon:arrow-left"

const message = useMessage()
const router = useRouter()
const dialog = useDialog()
const route = useRoute()
const loadingAgent = ref(false)
const agent = ref<Agent | null>(null)

const isOnline = computed(() => {
	return isAgentOnline(agent.value?.wazuh_last_seen ?? "")
})

function getAgent(id: string) {
	loadingAgent.value = true

	Api.agents
		.getAgents(id)
		.then(res => {
			if (res.data.success) {
				agent.value = res.data.agents[0] || null
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
				router.push(`/agents`).catch(() => {})
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			router.push(`/agents`).catch(() => {})
		})
		.finally(() => {
			loadingAgent.value = false
		})
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
				gotoAgents()
			},
			cbAfter: () => {
				loadingAgent.value = false
			}
		})
	}
}

function gotoAgents() {
	router.push(`/agents`).catch(() => {})
}

onBeforeMount(() => {
	if (route.params.id) {
		getAgent(route.params.id.toString())
	} else {
		router.replace(`/agents`).catch(() => {})
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
			.online-badge {
				border: 2px solid var(--primary-color);
				color: var(--primary-color);
				font-weight: bold;
				border-radius: var(--border-radius);
				@apply text-xs py-1 px-2;
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
