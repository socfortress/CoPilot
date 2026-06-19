<template>
	<CardEntity :loading :embedded :hoverable :clickable :highlighted="agent.critical_asset" @click="$emit('click')">
		<template #headerMain>
			<div class="flex items-center gap-3">
				<div v-if="selectable" class="selection-checkbox" @click.stop>
					<n-checkbox :checked="selected" @update:checked="$emit('toggle-selection')" />
				</div>
				<div class="text-default text-lg font-bold">
					{{ agent.hostname }}
				</div>
			</div>
		</template>
		<template #headerExtra>
			<div class="flex items-center gap-2">
				<n-tooltip>
					<span class="text-sm">
						{{ `${isOnline ? "online" : "last seen"}: ${formatLastSeen}` }}
					</span>
					<template #trigger>
						<n-tag v-if="isOnline" type="success" round class="rounded-lg!" :bordered="false" size="small">
							ONLINE
						</n-tag>
						<n-tag v-else round class="rounded-lg!" :bordered="false" size="small">OFFLINE</n-tag>
					</template>
				</n-tooltip>

				<n-tooltip>
					<span class="text-sm">Toggle Critical Assets</span>
					<template #trigger>
						<n-button
							:type="agent.critical_asset ? 'error' : 'default'"
							ghost
							size="tiny"
							@click.stop="toggleCritical(agent.agent_id, agent.critical_asset)"
						>
							<template #icon>
								<Icon :name="agent.critical_asset ? 'carbon:warning-alt' : 'carbon:checkmark'" />
							</template>
							{{ agent.critical_asset ? "Critical Asset" : "Non-Critical Asset" }}
						</n-button>
					</template>
				</n-tooltip>

				<n-tag v-if="agent.quarantined" type="warning" round class="rounded-lg!" :bordered="false" size="small">
					Quarantined
				</n-tag>
			</div>
		</template>

		<template #default>
			<div class="flex flex-wrap items-center gap-2">
				<Badge type="splitted" color="primary">
					<template #label>ID</template>
					<template #value>#{{ agent.agent_id }}</template>
				</Badge>
				<Badge type="splitted" color="primary">
					<template #label>label</template>
					<template #value>{{ agent.label }}</template>
				</Badge>
				<Badge type="splitted" color="primary">
					<template #label>OS</template>
					<template #value>
						<Icon :name="iconFromOs(agent.os)" :size="14" />
						{{ agent.os || "-" }}
					</template>
				</Badge>
				<Badge type="splitted" color="primary">
					<template #label>ip address</template>
					<template #value>
						{{ agent.ip_address || "-" }}
					</template>
				</Badge>
				<Badge type="splitted" color="primary">
					<template #label>wazuh agent status</template>
					<template #value>
						{{ agent.wazuh_agent_status || "-" }}
					</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div v-if="showActions" class="agent-actions">
				<div class="box flex items-center justify-end gap-4">
					<slot name="actions-left" />
					<n-tooltip to="body">
						<span class="text-sm">Delete Agent</span>
						<template #trigger>
							<n-button text type="error" size="small" @click.stop="handleDelete">
								<template #icon>
									<Icon :name="DeleteIcon" />
								</template>
								Delete
							</n-button>
						</template>
					</n-tooltip>
				</div>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents"
import { NButton, NCheckbox, NTag, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { AgentStatus } from "@/types/agents"
import { iconFromOs } from "@/utils"
import dayjs from "@/utils/dayjs"
import { handleDeleteAgent, toggleAgentCritical } from "./utils"

const props = defineProps<{
	agent: Agent
	showActions?: boolean
	embedded?: boolean
	hoverable?: boolean
	clickable?: boolean
	selectable?: boolean
	selected?: boolean
}>()

const emit = defineEmits<{
	(e: "delete"): void
	(e: "click"): void
	(e: "toggle-selection"): void
}>()

const { agent, showActions, embedded, hoverable, clickable, selectable, selected } = toRefs(props)

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
