<template>
	<div>
		<CardEntity hoverable clickable :embedded class="@container" @click.stop="showDetails = true">
			<template #headerMain>#{{ alert._id || alert._source.id }}</template>
			<template #headerExtra>
				{{ formatDate(alert._source.timestamp_utc, dFormats.datetimesec) }}
			</template>
			<template #default>
				<div class="flex flex-col gap-1">
					{{ alert._source.rule_description || alert._source.type }}
					<p>
						{{ alert._source.rule_groups }}
					</p>
				</div>
			</template>
			<template v-if="alert._id" #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TargetIcon" :size="13" class="opacity-80!" />
						</template>
						<template #label>Fired times</template>
						<template #value>
							{{ alert._source.rule_firedtimes }}
						</template>
					</Badge>

					<Badge :type="alert._source.rule_mail ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="alert._source.rule_mail ? MailIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>Rule mail</template>
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
										{{ alert._source.agent_name }} / {{ alert._source.agent_labels_customer }}
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
									@click.stop="routeAgent(alert._source.agent_id)"
								>
									{{ alert._source.agent_id }}
									<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
								</code>
							</div>
							<div class="box">
								agent_ip:
								<code>{{ alert._source.agent_ip }}</code>
							</div>
							<div class="box">
								agent_name:
								<code>{{ alert._source.agent_name }}</code>
							</div>
							<div class="box">
								agent_labels_customer:
								<code
									class="text-primary cursor-pointer"
									@click.stop="routeCustomer({ code: alert._source.agent_labels_customer })"
								>
									{{ alert._source.agent_labels_customer }}
									<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
								</code>
							</div>
						</div>
					</n-popover>
					<Badge type="splitted" color="primary">
						<template #label>syslog</template>
						<template #value>{{ alert._source.syslog_type }} / {{ alert._source.syslog_level }}</template>
					</Badge>
					<Badge type="splitted" color="primary" class="hidden! @2xl:flex!">
						<template #label>manager</template>
						<template #value>
							{{ alert._source.manager_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="hidden! @2xl:flex!">
						<template #label>decoder</template>
						<template #value>
							{{ alert._source.decoder_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="hidden! @2xl:flex!">
						<template #label>source</template>
						<template #value>
							{{ alert._source.source }}
						</template>
					</Badge>
				</div>
			</template>
			<template v-if="!hideActions" #footerExtra>
				<AlertActions
					:alert
					:soc-alert-field="socAlertCreationField"
					size="small"
					@start-loading="loading = true"
					@stop-loading="loading = false"
					@updated-url="alert._source.alert_url = $event"
					@updated-id="alert._source.alert_id = $event"
					@updated-ask-message="alert._source.ask_socfortress_message = $event"
				/>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Alert: ${alert._id || alert._source.id}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane v-if="alert._id" name="Agent" tab="Agent" display-directive="show">
					<div v-if="agentProperties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of agentProperties" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								<template v-if="key === 'agent_id'">
									<code class="text-primary cursor-pointer" @click.stop="routeAgent(`${value}`)">
										{{ value }}
										<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
									</code>
								</template>
								<template v-else-if="key === 'agent_labels_customer'">
									<code
										class="text-primary cursor-pointer"
										@click.stop="routeCustomer(value ? { code: value.toString() } : undefined)"
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
				<n-tab-pane
					v-if="alert._source.ask_socfortress_message"
					name="SOCFortress Response"
					tab="SOCFortress Response"
					display-directive="show"
				>
					<div class="p-7 pt-4">
						<n-input
							:value="alert._source.ask_socfortress_message"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane v-if="alert._source.message" name="Message" tab="Message" display-directive="show">
					<div class="p-7 pt-4">
						<CodeSource :code="alert._source.message" :decode="false" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="alert._source.data_document"
					name="Data document"
					tab="Data document"
					display-directive="show"
				>
					<div class="p-7 pt-4">
						<n-input
							:value="alert._source.data_document"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<CodeSource :code="alert._source" lang="json" :decode="false" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SocAlertField } from "./type.d"
import type { Alert } from "@/types/alerts.d"
import _pick from "lodash/pick"
import { NInput, NModal, NPopover, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, inject, ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const props = defineProps<{ alert: Alert; hideActions?: boolean; embedded?: boolean }>()
const AlertActions = defineAsyncComponent(() => import("./AlertActions.vue"))
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const { alert, hideActions, embedded } = toRefs(props)

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const DisabledIcon = "carbon:subtract"
const MailIcon = "carbon:email"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"

const { routeCustomer, routeAgent } = useNavigation()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const agentProperties = computed(() => {
	return _pick(alert.value._source, [
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

const socAlertCreationField = ref(inject<SocAlertField>("soc-alert-creation-field", "alert_url"))
</script>
