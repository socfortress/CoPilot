<template>
	<div class="customer-healthcheck-item" :class="[{ 'bg-secondary': bgSecondary }, type]">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
					<span>#{{ healthData.id }} - {{ healthData.label }}</span>
					<Icon :name="InfoIcon" :size="16"></Icon>
				</div>
				<div class="time" v-if="cardDate">
					{{ cardDate }}
				</div>
			</div>

			<div class="main-box">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">
						<Icon :name="iconFromOs(healthData.os)" :size="16" class="mr-1 relative top-0.5"></Icon>
						{{ healthData.os }}
					</div>
					<div class="description">
						{{ healthData.ip_address }}
					</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<Badge type="splitted" v-if="agentVersion">
					<template #label>Agent version</template>
					<template #value>{{ agentVersion }}</template>
				</Badge>

				<Badge type="splitted" v-if="source === 'velociraptor'">
					<template #label>Velociraptor Id</template>
					<template #value>{{ healthData.velociraptor_id }}</template>
				</Badge>

				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<Badge type="splitted" hint-cursor>
							<template #iconLeft>
								<Icon :name="AgentIcon" :size="13" class="!opacity-80"></Icon>
							</template>
							<template #label>Agent</template>
							<template #value>
								{{ healthData.hostname }}
							</template>
						</Badge>
					</template>
					<div class="flex flex-col gap-1">
						<div class="box">
							agent_id:
							<code class="cursor-pointer text-primary-color" @click="gotoAgent(healthData.agent_id)">
								{{ healthData.agent_id }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</div>
						<div class="box">
							hostname:
							<code>{{ healthData.hostname }}</code>
						</div>
					</div>
				</n-popover>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:title="`Health check ${source}`"
			:bordered="false"
			segmented
		>
			<div class="grid gap-2 grid-auto-flow-200 px-7 py-6">
				<KVCard v-for="(value, key) of healthData" :key="key">
					<template #key>{{ key }}</template>
					<template #value>{{ value || "-" }}</template>
				</KVCard>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref } from "vue"
import KVCard from "@/components/common/KVCard.vue"
import { NPopover, NModal } from "naive-ui"
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers.d"
import dayjs from "@/utils/dayjs"
import { iconFromOs } from "@/utils"
import { useSettingsStore } from "@/stores/settings"
import { useGoto } from "@/composables/useGoto"

const { healthData, source, bgSecondary, type } = defineProps<{
	healthData: CustomerAgentHealth
	source: CustomerHealthcheckSource
	type?: "healthy" | "unhealthy"
	bgSecondary?: boolean
}>()

const InfoIcon = "carbon:information"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"

const showDetails = ref(false)
const { gotoAgent } = useGoto()

const agentVersion = computed(() => {
	let agent = ""

	switch (source) {
		case "wazuh":
			agent = healthData.wazuh_agent_version
			break
		case "velociraptor":
			agent = healthData.velociraptor_agent_version
			break
	}

	return agent
})

const cardDate = computed(() => {
	let date = ""
	switch (source) {
		case "wazuh":
			date = healthData.wazuh_last_seen
			break
		case "velociraptor":
			date = healthData.velociraptor_last_seen
			break
	}

	return date ? formatDate(date) : ""
})

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}
</script>

<style lang="scss" scoped>
.customer-healthcheck-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	&.bg-secondary {
		background-color: var(--bg-secondary-color);
	}

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;

		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;

			&:hover {
				color: var(--primary-color);
			}
		}

		.time {
			color: var(--fg-secondary-color);
		}
	}

	.main-box {
		.content {
			word-break: break-word;

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	&.healthy {
		border-color: var(--success-color);
	}
	&.unhealthy {
		border-color: var(--warning-color);

		.header-box {
			.id {
				&:hover {
					color: var(--warning-color);
				}
			}
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);

		&.healthy {
			background-color: var(--success-005-color);
			box-shadow: none;
		}
		&.unhealthy {
			background-color: var(--secondary3-opacity-005-color);
			box-shadow: none;
		}
	}
}
</style>
