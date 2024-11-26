<template>
	<div>
		<CardEntity
			:embedded
			hoverable
			clickable
			:status="type === 'healthy' ? 'success' : type === 'unhealthy' ? 'warning' : undefined"
			@click="(showDetails = true)"
		>
			<template #headerMain>#{{ healthData.id }} - {{ healthData.label }}</template>
			<template v-if="cardDate" #headerExtra>{{ cardDate }}</template>
			<template #default>
				<div class="flex grow flex-col gap-1">
					<div class="flex flex-wrap items-center gap-2">
						<Icon :name="iconFromOs(healthData.os)" :size="16"></Icon>
						{{ healthData.os }}
					</div>
					<p>
						{{ healthData.ip_address }}
					</p>
				</div>
			</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge v-if="agentVersion" type="splitted">
						<template #label>Agent version</template>
						<template #value>
							{{ agentVersion }}
						</template>
					</Badge>

					<Badge v-if="source === 'velociraptor'" type="splitted">
						<template #label>Velociraptor Id</template>
						<template #value>
							{{ healthData.velociraptor_id }}
						</template>
					</Badge>

					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<Badge type="splitted" hint-cursor>
								<template #iconLeft>
									<Icon :name="AgentIcon" :size="13" class="!opacity-80"></Icon>
								</template>
								<template #label>Agent</template>
								<template #value>
									<div class="flex items-center gap-2">
										{{ healthData.hostname }}
										<Icon :name="InfoIcon" :size="14"></Icon>
									</div>
								</template>
							</Badge>
						</template>
						<div class="flex flex-col gap-1">
							<div class="box">
								agent_id:
								<code class="text-primary cursor-pointer" @click="gotoAgent(healthData.agent_id)">
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
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:title="`Health check ${source}`"
			:bordered="false"
			segmented
		>
			<div class="grid-auto-fit-200 grid gap-2 px-7 py-6">
				<CardKV v-for="(value, key) of healthData" :key="key">
					<template #key>
						{{ key }}
					</template>
					<template #value>
						{{ value || "-" }}
					</template>
				</CardKV>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers.d"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { iconFromOs } from "@/utils"
import dayjs from "@/utils/dayjs"
import { NModal, NPopover } from "naive-ui"
import { computed, ref } from "vue"

const { healthData, source, embedded, type } = defineProps<{
	healthData: CustomerAgentHealth
	source: CustomerHealthcheckSource
	type?: "healthy" | "unhealthy"
	embedded?: boolean
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
