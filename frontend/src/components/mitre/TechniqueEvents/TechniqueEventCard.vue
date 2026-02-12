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
								<code class="text-primary cursor-pointer" @click.stop="routeAgent(alert.agent_id)">
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
									@click.stop="routeCustomer({ code: alert.agent_labels_customer })"
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
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Agent" tab="Agent" display-directive="show">
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

				<template v-if="!useDetailsTab">
					<n-tab-pane
						v-for="tabCard of tabsCards"
						:key="tabCard.tab"
						:name="tabCard.tab"
						:tab="tabCard.tab"
						display-directive="show"
					>
						<div v-if="tabCard.properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
							<CardKV v-for="(value, key) of tabCard.properties" :key="key">
								<template #key>
									{{ key }}
								</template>
								<template #value>
									{{ value || "-" }}
								</template>
							</CardKV>
						</div>
					</n-tab-pane>

					<n-tab-pane name="DNS" tab="DNS" display-directive="show">
						<div class="px-7 pt-4">
							<CardKV v-if="alert.data_dns_answers">
								<template #key>data_dns_answers</template>
								<template #value>
									<CodeSource :code="alert.data_dns_answers" :decode="false" />
								</template>
							</CardKV>
						</div>
						<div v-if="dnsProperties" class="grid-auto-fit-200 grid gap-2 p-7 pt-2">
							<CardKV v-for="(value, key) of dnsProperties" :key="key">
								<template #key>
									{{ key }}
								</template>
								<template #value>
									{{ value || "-" }}
								</template>
							</CardKV>
						</div>
					</n-tab-pane>

					<n-tab-pane name="GL2" tab="GL2" display-directive="show">
						<div class="px-7 pt-4">
							<CardKV v-if="alert.gl2_processing_error">
								<template #key>gl2_processing_error</template>
								<template #value>
									{{ alert.gl2_processing_error }}
								</template>
							</CardKV>
						</div>
						<div v-if="gl2Properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-2">
							<CardKV v-for="(value, key) of gl2Properties" :key="key">
								<template #key>
									{{ key }}
								</template>
								<template #value>
									{{ value || "-" }}
								</template>
							</CardKV>
						</div>
					</n-tab-pane>

					<n-tab-pane v-if="alert.message" name="Message" tab="Message" display-directive="show">
						<div class="p-7 pt-4">
							<CodeSource :code="alert.message" :decode="false" />
						</div>
					</n-tab-pane>

					<n-tab-pane v-if="alert.location" name="Location" tab="Location" display-directive="show">
						<div class="p-7 pt-4">
							<CodeSource :code="alert.location" :decode="false" />
						</div>
					</n-tab-pane>

					<n-tab-pane v-if="alert.streams?.length" name="Streams" tab="Streams" display-directive="show">
						<div class="flex flex-wrap gap-3 p-7 pt-4">
							<ul>
								<li v-for="stream of alert.streams" :key="stream">
									<code>{{ stream }}</code>
								</li>
							</ul>
						</div>
					</n-tab-pane>
				</template>

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
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	alert: MitreEventDetails
	hideActions?: boolean
	embedded?: boolean
	useDetailsTab?: boolean
}>()
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const { alert, embedded, useDetailsTab } = toRefs(props)

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"

const { routeCustomer, routeAgent } = useNavigation()
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const tabsCards = computed(() => [
	{
		tab: "Host",
		properties: _pick(alert.value, [
			"data_host_architecture",
			"data_host_id",
			"data_host_mac",
			"data_host_name",
			"data_host_hostname",
			"data_host_containerized",
			"data_host_ip",
			"data_host_os_codename",
			"data_host_os_family",
			"data_host_os_kernel",
			"data_host_os_name",
			"data_host_os_platform",
			"data_host_os_type",
			"data_host_os_version"
		])
	},
	{
		tab: "Network",
		properties: _pick(alert.value, [
			"data_network_protocol",
			"data_network_transport",
			"data_network_type",
			"data_network_bytes",
			"data_network_direction",
			"data_network_community_id",
			"traffic_direction"
		])
	},
	{
		tab: "Event",
		properties: _pick(alert.value, [
			"data_event_category",
			"data_event_dataset",
			"data_event_duration",
			"data_event_end",
			"data_event_kind",
			"data_event_start",
			"data_event_type",
			"data_type"
		])
	},
	{
		tab: "Timestamp",
		properties: _pick(alert.value, ["timestamp", "timestamp_utc", "data_@timestamp", "msg_timestamp"])
	},
	{
		tab: "Source",
		properties: _pick(alert.value, ["data_source_ip", "data_source_port", "data_source_bytes"])
	},
	{
		tab: "Destination",
		properties: _pick(alert.value, ["data_destination_ip", "data_destination_port", "data_destination_bytes"])
	},
	{
		tab: "Client",
		properties: _pick(alert.value, ["data_client_ip", "data_client_port", "data_client_bytes"])
	},
	{
		tab: "Server",
		properties: _pick(alert.value, ["data_server_ip", "data_server_port", "data_server_bytes"])
	},
	{
		tab: "Cluster",
		properties: _pick(alert.value, ["cluster_name", "cluster_node"])
	},
	{
		tab: "Rule",
		properties: _pick(alert.value, [
			"rule_id",
			"rule_level",
			"rule_mail",
			"rule_mitre_id",
			"rule_mitre_tactic",
			"rule_mitre_technique",
			"rule_description",
			"rule_firedtimes",
			"rule_groups",
			"rule_group1",
			"rule_group2",
			"rule_group3"
		])
	}
])

const agentProperties = computed(() => {
	return _pick(alert.value, [
		"agent_id",
		"agent_name",
		"agent_ip",
		"data_agent_id",
		"data_agent_name",
		"data_agent_type",
		"data_agent_version",
		"data_agent_ephemeral_id",
		"agent_labels_customer"
	])
})

const dnsProperties = computed(() => {
	return _pick(alert.value, [
		"data_dns_answers_count",
		"data_dns_authorities_count",
		"data_dns_flags_authentic_data",
		"data_dns_flags_authoritative",
		"data_dns_flags_checking_disabled",
		"data_dns_flags_recursion_available",
		"data_dns_flags_recursion_desired",
		"data_dns_flags_truncated_response",
		"data_dns_header_flags",
		"data_dns_id",
		"data_dns_op_code",
		"data_dns_opt_do",
		"data_dns_opt_ext_rcode",
		"data_dns_opt_udp_size",
		"data_dns_opt_version",
		"data_dns_question_class",
		"data_dns_question_etld_plus_one",
		"data_dns_question_name",
		"data_dns_question_registered_domain",
		"data_dns_question_subdomain",
		"data_dns_question_top_level_domain",
		"data_dns_question_type",
		"data_dns_resolved_ip",
		"data_dns_response_code",
		"data_dns_type",
		"dns_query",
		"dns_response_code",
		"dns_answer"
	])
})

const gl2Properties = computed(() => {
	return _pick(alert.value, [
		"gl2_remote_ip",
		"gl2_source_node",
		"gl2_accounted_message_size",
		"gl2_remote_port",
		"gl2_source_input",
		"gl2_message_id"
	])
})
</script>
