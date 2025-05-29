<template>
	<CardEntity class="agent-card" :loading :embedded :hoverable :clickable :class="{ critical: agent.critical_asset }">
		<div class="wrapper">
			<div class="agent-header">
				<div class="title">
					<n-tooltip>
						{{ `${isOnline ? "online" : "last seen"} - ${formatLastSeen}` }}
						<template #trigger>
							<div class="hostname" :class="{ online: isOnline }">
								{{ agent.hostname }}
							</div>
						</template>
					</n-tooltip>
					<div class="critical" :class="{ active: agent.critical_asset }">
						<n-tooltip>
							Toggle Critical Assets
							<template #trigger>
								<n-button
									quaternary
									circle
									:type="agent.critical_asset ? 'warning' : 'default'"
									@click.stop="toggleCritical(agent.agent_id, agent.critical_asset)"
								>
									<template #icon>
										<Icon :name="StarIcon"></Icon>
									</template>
								</n-button>
							</template>
						</n-tooltip>
					</div>
					<div v-show="agent.quarantined" class="quarantined">
						<n-tooltip>
							Quarantined
							<template #trigger>
								<Icon :name="QuarantinedIcon" :size="18"></Icon>
							</template>
						</n-tooltip>
					</div>
				</div>
				<div class="info">#{{ agent.agent_id }} / {{ agent.label }}</div>
			</div>
			<div class="agent-info">
				<div class="os" :title="agent.os">
					{{ agent.os }}
				</div>
				<div class="ip-address" :title="agent.ip_address">
					{{ agent.ip_address }}
				</div>
			</div>

			<div v-if="showActions" class="agent-actions">
				<div class="box">
					<n-tooltip>
						Delete
						<template #trigger>
							<n-button quaternary circle type="error" @click.stop="handleDelete">
								<template #icon>
									<Icon :name="DeleteIcon"></Icon>
								</template>
							</n-button>
						</template>
					</n-tooltip>
				</div>
			</div>
		</div>
	</CardEntity>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import { NButton, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { AgentStatus } from "@/types/agents.d"
import dayjs from "@/utils/dayjs"
import { handleDeleteAgent, toggleAgentCritical } from "./utils"

const props = defineProps<{
	agent: Agent
	showActions?: boolean
	embedded?: boolean
	hoverable?: boolean
	clickable?: boolean
}>()

const emit = defineEmits<{
	(e: "delete"): void
}>()

const { agent, showActions, embedded, hoverable, clickable } = toRefs(props)

const QuarantinedIcon = "ph:seal-warning-light"
const StarIcon = "carbon:star"
const DeleteIcon = "ph:trash"
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const message = useMessage()
const dialog = useDialog()
const isOnline = computed(() => {
	return agent.value.wazuh_agent_status === AgentStatus.Active
})
const formatLastSeen = computed(() => {
	const lastSeenDate = dayjs(agent.value.wazuh_last_seen)
	if (!lastSeenDate.isValid()) return agent.value.wazuh_last_seen

	return lastSeenDate.format(dFormats.datetime)
})

function handleDelete() {
	handleDeleteAgent({
		agent: agent.value,
		cbBefore: () => {
			loading.value = true
		},
		cbSuccess: () => {
			emit("delete")
		},
		cbAfter: () => {
			loading.value = false
		},
		message,
		dialog
	})
}

function toggleCritical(agentId: string, criticalStatus: boolean) {
	toggleAgentCritical({
		agentId,
		criticalStatus,
		message,
		cbBefore: () => {
			loading.value = true
		},
		cbSuccess: () => {
			agent.value.critical_asset = !criticalStatus
		},
		cbAfter: () => {
			loading.value = false
		}
	})
}
</script>

<style lang="scss" scoped>
.agent-card {
	container-type: inline-size;

	.wrapper {
		display: flex;
		flex-direction: row;
		align-items: center;
		gap: calc(var(--spacing) * 6);
		overflow: hidden;

		.agent-header {
			display: flex;
			flex-direction: column;
			min-width: 300px;

			.title {
				display: flex;
				align-items: center;
				gap: calc(var(--spacing) * 2);
				margin-bottom: 4px;

				.hostname {
					font-weight: bold;
					white-space: nowrap;
					line-height: 32px;
					height: 32px;
					border-radius: 4px;
					border: 1px solid var(--info-color);
					border-color: transparent;
					box-sizing: border-box;
					overflow: hidden;
					text-overflow: ellipsis;

					&.online {
						padding: 0px 15px;
						color: var(--success-color);
						border-color: var(--success-color);
					}
				}

				.quarantined {
					display: flex;
					padding-top: 1px;
					color: var(--warning-color);
				}
			}
			.info {
				font-family: var(--font-family-mono);
				font-size: var(--text-xs);
				opacity: 0.7;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
				margin-left: 2px;
			}
		}

		.agent-info {
			display: flex;
			flex-direction: column;
			flex-grow: 1;
			overflow: hidden;

			.os {
				line-height: 32px;
				height: 32px;
				margin-bottom: 4px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.ip-address {
				white-space: nowrap;
				font-size: var(--text-xs);
				font-family: var(--font-family-mono);
				opacity: 0.7;
				overflow: hidden;
				text-overflow: ellipsis;
			}
		}

		.agent-actions {
			display: flex;
		}
	}

	&.critical {
		border-color: var(--warning-color);
	}

	@container (max-width: 550px) {
		.wrapper {
			gap: calc(var(--spacing) * 5);

			.agent-header {
				min-width: initial;
			}
		}
	}
	@container (max-width: 400px) {
		.wrapper {
			gap: calc(var(--spacing) * 4);

			.agent-header {
				flex-grow: 1;
				overflow: hidden;
			}
			.agent-info {
				display: none;
			}
		}
	}
}
</style>
