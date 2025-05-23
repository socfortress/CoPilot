<template>
	<div>
		<CardEntity hoverable clickable :embedded class="@container" @click.stop="showDetails = true">
			<template #headerMain>#{{ alert.id }}</template>
			<template #headerExtra>
				{{ formatDate(alert.timestamp_utc, dFormats.datetimesec) }}
			</template>
			<template #default>
				<div class="flex flex-col gap-1">
					{{ alert.rule_description }}
					<p>
						{{ alert.rule_groups }}
					</p>
				</div>
			</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TargetIcon" :size="13" class="!opacity-80" />
						</template>
						<template #label>Fired times</template>
						<template #value>
							{{ alert.rule_firedtimes }}
						</template>
					</Badge>

					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<Badge type="splitted" color="primary" hint-cursor>
								<template #iconLeft>
									<Icon :name="AgentIcon" :size="13" class="!opacity-80" />
								</template>
								<template #label>Agent</template>
								<template #value>
									<div class="flex flex-wrap items-center gap-2">
										{{ alert.agent_name }} / {{ alert.agent_labels_customer }}
										<Icon :name="InfoIcon" :size="13" class="!opacity-80" />
									</div>
								</template>
							</Badge>
						</template>
						<div class="flex flex-col gap-1">
							<div class="box">
								agent_id:
								<code class="text-primary cursor-pointer" @click.stop="gotoAgent(alert.agent_id)">
									{{ alert.agent_id }}
									<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
								</code>
							</div>
							<div class="box">
								agent_ip:
								<code>{{ alert.agent_ip }}</code>
							</div>
							<div class="box">
								agent_name:
								<code>{{ alert.agent_name }}</code>
							</div>
							<div class="box">
								agent_labels_customer:
								<code
									class="text-primary cursor-pointer"
									@click.stop="gotoCustomer({ code: alert.agent_labels_customer })"
								>
									{{ alert.agent_labels_customer }}
									<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
								</code>
							</div>
						</div>
					</n-popover>
					<Badge type="splitted" color="primary">
						<template #label>syslog</template>
						<template #value>{{ alert.syslog_type }} / {{ alert.syslog_level }}</template>
					</Badge>
					<Badge type="splitted" color="primary" class="@2xl:!flex !hidden">
						<template #label>manager</template>
						<template #value>
							{{ alert.manager_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="@2xl:!flex !hidden">
						<template #label>decoder</template>
						<template #value>
							{{ alert.decoder_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="@2xl:!flex !hidden">
						<template #label>source</template>
						<template #value>
							{{ alert.source }}
						</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Alert: ${alert.id}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Agent" tab="Agent" display-directive="show">
					<div v-if="agentProperties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of agentProperties" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								<template v-if="key === 'agent_id'">
									<code class="text-primary cursor-pointer" @click.stop="gotoAgent(`${value}`)">
										{{ value }}
										<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
									</code>
								</template>
								<template v-else-if="key === 'agent_labels_customer'">
									<code
										class="text-primary cursor-pointer"
										@click.stop="gotoCustomer(value ? { code: value.toString() } : undefined)"
									>
										{{ value }}
										<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
									</code>
								</template>
								<template v-else>
									{{ value || "-" }}
								</template>
							</template>
						</CardKV>
					</div>
				</n-tab-pane>

				<n-tab-pane v-if="alert.message" name="Message" tab="Message" display-directive="show">
					<div class="p-7 pt-4">
						<CodeSource :code="alert.message" :decode="false" />
					</div>
				</n-tab-pane>

				<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<CodeSource :code="alert" lang="json" :decode="false" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreEventDetails } from "@/types/mitre.d"
import _pick from "lodash/pick"
import { NModal, NPopover, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const props = defineProps<{ alert: MitreEventDetails; hideActions?: boolean; embedded?: boolean }>()
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const { alert, embedded } = toRefs(props)

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const DisabledIcon = "carbon:subtract"
const MailIcon = "carbon:email"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"

const { gotoCustomer, gotoAgent } = useGoto()
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const agentProperties = computed(() => {
	return _pick(alert.value, [
		"agent_id",
		"agent_ip_city_name",
		"agent_ip_country_code",
		"agent_ip_geolocation",
		"agent_ip_reserved_ip",
		"agent_ip",
		"agent_labels_customer",
		"agent_name"
	])
})
</script>
