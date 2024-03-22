<template>
	<n-card
		class="agent-card py-3 px-4"
		:class="{ critical: agent.critical_asset, 'bg-secondary': bgSecondary }"
		content-style="padding:0"
	>
		<n-spin :show="loading">
			<div class="wrapper">
				<div class="agent-header">
					<div class="title">
						<n-tooltip>
							{{ `${isOnline ? "online" : "last seen"} - ${formatLastSeen}` }}
							<template #trigger>
								<div class="hostname" :class="{ online: isOnline }">{{ agent.hostname }}</div>
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
						<div class="quarantined" v-show="agent.quarantined">
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
					<div class="ip-address" :title="agent.ip_address">{{ agent.ip_address }}</div>
				</div>

				<div class="agent-actions" v-if="showActions">
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
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from "vue"
import { AgentStatus, type Agent } from "@/types/agents.d"
import dayjs from "@/utils/dayjs"
import { handleDeleteAgent, toggleAgentCritical } from "./utils"
import { NTooltip, NButton, NSpin, NCard, useMessage, useDialog } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"

const QuarantinedIcon = "ph:seal-warning-light"
const StarIcon = "carbon:star"
const DeleteIcon = "ph:trash"

const emit = defineEmits<{
	(e: "delete"): void
}>()

const props = defineProps<{
	agent: Agent
	showActions?: boolean
	bgSecondary?: boolean
}>()
const { agent, showActions, bgSecondary } = toRefs(props)

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
	overflow: hidden;
	border: 2px solid transparent;
	max-width: 100%;
	box-sizing: border-box;
	cursor: pointer;
	transition: all 0.3s;
	border: var(--border-small-050);

	&.bg-secondary {
		background-color: var(--bg-secondary-color);
	}

	.wrapper {
		display: flex;
		@apply gap-6;
		flex-direction: row;
		align-items: center;
		overflow: hidden;

		.agent-header {
			display: flex;
			flex-direction: column;
			min-width: 300px;

			.title {
				display: flex;
				align-items: center;
				@apply gap-2;
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
				@apply text-xs;
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
				@apply text-xs;
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

	&:hover {
		border-color: var(--primary-color);
	}

	&.critical {
		border-color: var(--warning-color);
	}

	@container (max-width: 550px) {
		.wrapper {
			@apply gap-5;

			.agent-header {
				min-width: initial;
			}
		}
	}
	@container (max-width: 400px) {
		.wrapper {
			@apply gap-4;

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
