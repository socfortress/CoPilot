<template>
	<div>
		<CardEntity hoverable :embedded class="@container">
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
							<Icon :name="TargetIcon" :size="13" class="opacity-80!" />
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
									<Icon :name="AgentIcon" :size="13" class="opacity-80!" />
								</template>
								<template #label>Agent</template>
								<template #value>
									<div class="flex flex-wrap items-center gap-2">
										{{ alert.agent_name }} / {{ alert.agent_labels_customer }}
										<Icon :name="InfoIcon" :size="13" class="opacity-80!" />
									</div>
								</template>
							</Badge>
						</template>
						<div class="flex flex-col gap-1">
							<div class="box">
								agent_id:
								<code
									class="text-primary cursor-pointer"
									@click.stop="routeAgent(alert.agent_id).navigate()"
								>
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
									@click.stop="routeCustomer({ code: alert.agent_labels_customer }).navigate()"
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
					<Badge type="splitted" color="primary" class="hidden! @2xl:flex!">
						<template #label>manager</template>
						<template #value>
							{{ alert.manager_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="hidden! @2xl:flex!">
						<template #label>decoder</template>
						<template #value>
							{{ alert.decoder_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="hidden! @2xl:flex!">
						<template #label>source</template>
						<template #value>
							{{ alert.source }}
						</template>
					</Badge>
				</div>
			</template>
			<template v-if="!hideActions" #footerExtra>
				<EntityDetailsButton
					size="small"
					:url="routeAlertsMitreEvent(techniqueId, alert.id).fullUrl()"
					@view="showDetails = true"
				/>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Alert: ${alert.id}`"
			:bordered="false"
			segmented
		>
			<TechniqueEventOverview :alert :use-details-tab />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreEventDetails } from "@/types/mitre"
import { NModal, NPopover } from "naive-ui"
import { ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import TechniqueEventOverview from "./TechniqueEventOverview.vue"

const props = defineProps<{
	alert: MitreEventDetails
	techniqueId: string
	hideActions?: boolean
	embedded?: boolean
	useDetailsTab?: boolean
}>()

const { alert, embedded, useDetailsTab, hideActions, techniqueId } = toRefs(props)

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"

const { routeCustomer, routeAgent, routeAlertsMitreEvent } = useNavigation()
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat
</script>
