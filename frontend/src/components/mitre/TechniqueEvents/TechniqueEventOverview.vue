<template>
	<n-spin :show="loadingDetails">
		<n-tabs v-if="resolvedAlert" type="line" animated :tabs-padding="fullWidth ? 0 : 24">
			<n-tab-pane name="Agent" tab="Agent" display-directive="show">
				<div v-if="agentProperties" class="grid-auto-fit-200 grid gap-2" :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
				<CardKV v-for="(value, key) of agentProperties" :key>
					<template #key>
						{{ key }}
					</template>
					<template #value>
						<template v-if="key === 'agent_id'">
							<code class="text-primary cursor-pointer" @click.stop="routeAgent(`${value}`).navigate()">
								{{ value }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
						<template v-else-if="key === 'agent_labels_customer'">
							<code
								class="text-primary cursor-pointer"
								@click.stop="routeCustomer(value ? { code: value.toString() } : undefined).navigate()"
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
				<div v-if="tabCard.properties" class="grid-auto-fit-200 grid gap-2" :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
					<CardKV v-for="(value, key) of tabCard.properties" :key>
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
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3'">
					<CardKV v-if="resolvedAlert.data_dns_answers">
						<template #key>data_dns_answers</template>
						<template #value>
							<CodeSource :code="resolvedAlert.data_dns_answers" :decode="false" />
						</template>
					</CardKV>
				</div>
				<div v-if="dnsProperties" class="grid-auto-fit-200 grid gap-2" :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
					<CardKV v-for="(value, key) of dnsProperties" :key>
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
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3'">
					<CardKV v-if="resolvedAlert.gl2_processing_error">
						<template #key>gl2_processing_error</template>
						<template #value>
							{{ resolvedAlert.gl2_processing_error }}
						</template>
					</CardKV>
				</div>
				<div v-if="gl2Properties" class="grid-auto-fit-200 grid gap-2" :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
					<CardKV v-for="(value, key) of gl2Properties" :key>
						<template #key>
							{{ key }}
						</template>
						<template #value>
							{{ value || "-" }}
						</template>
					</CardKV>
				</div>
			</n-tab-pane>

			<n-tab-pane v-if="resolvedAlert.message" name="Message" tab="Message" display-directive="show">
				<div :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
					<CodeSource :code="resolvedAlert.message" :decode="false" />
				</div>
			</n-tab-pane>

			<n-tab-pane v-if="resolvedAlert.location" name="Location" tab="Location" display-directive="show">
				<div :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
					<CodeSource :code="resolvedAlert.location" :decode="false" />
				</div>
			</n-tab-pane>

			<n-tab-pane v-if="resolvedAlert.streams?.length" name="Streams" tab="Streams" display-directive="show">
				<div class="flex flex-wrap gap-3" :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
					<ul>
						<li v-for="stream of resolvedAlert.streams" :key="stream">
							<code>{{ stream }}</code>
						</li>
					</ul>
				</div>
			</n-tab-pane>
		</template>

		<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
			<div :class="fullWidth ? 'p-0' : 'p-6 pt-3'">
				<CodeSource :code="resolvedAlert" lang="json" :decode="false" />
			</div>
		</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import type { MitreEventsQuery } from "@/api/endpoints/wazuh/mitre"
import type { ApiError } from "@/types/common"
import type { MitreEventDetails } from "@/types/mitre"
import _pick from "lodash/pick"
import { NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	alert?: MitreEventDetails
	techniqueId?: string
	eventId?: string
	timeRange?: string
	useDetailsTab?: boolean
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreEventDetails): void
}>()

const { useDetailsTab } = toRefs(props)

const message = useMessage()
const loadingDetails = ref(false)
const fetchedAlert = ref<MitreEventDetails | undefined>(undefined)

const resolvedAlert = computed(() => props.alert ?? fetchedAlert.value)

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const LinkIcon = "carbon:launch"

const { routeCustomer, routeAgent } = useNavigation()

function getDetails() {
	if (!props.techniqueId || !props.eventId) return

	loadingDetails.value = true

	const query: MitreEventsQuery = {
		technique_id: props.techniqueId,
		alert_id: props.eventId,
		size: 1,
		page: 1,
		index_pattern: "*",
		time_range: props.timeRange ?? "now-7d"
	}

	Api.wazuh.mitre
		.getMitreEvents(query)
		.then(res => {
			if (res.data.success) {
				if (res.data.alerts?.[0]) {
					fetchedAlert.value = res.data.alerts[0]
					emit("loaded", res.data.alerts[0])
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDetails.value = false
		})
}

onBeforeMount(() => {
	if (props.alert) return
	if (props.techniqueId && props.eventId) getDetails()
})

const tabsCards = computed(() => {
	if (!resolvedAlert.value) return []

	return [
	{
		tab: "Host",
		properties: _pick(resolvedAlert.value, [
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
		properties: _pick(resolvedAlert.value, [
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
		properties: _pick(resolvedAlert.value, [
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
		properties: _pick(resolvedAlert.value, ["timestamp", "timestamp_utc", "data_@timestamp", "msg_timestamp"])
	},
	{
		tab: "Source",
		properties: _pick(resolvedAlert.value, ["data_source_ip", "data_source_port", "data_source_bytes"])
	},
	{
		tab: "Destination",
		properties: _pick(resolvedAlert.value, ["data_destination_ip", "data_destination_port", "data_destination_bytes"])
	},
	{
		tab: "Client",
		properties: _pick(resolvedAlert.value, ["data_client_ip", "data_client_port", "data_client_bytes"])
	},
	{
		tab: "Server",
		properties: _pick(resolvedAlert.value, ["data_server_ip", "data_server_port", "data_server_bytes"])
	},
	{
		tab: "Cluster",
		properties: _pick(resolvedAlert.value, ["cluster_name", "cluster_node"])
	},
	{
		tab: "Rule",
		properties: _pick(resolvedAlert.value, [
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
]
})

const agentProperties = computed(() => {
	if (!resolvedAlert.value) return undefined

	return _pick(resolvedAlert.value, [
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
	if (!resolvedAlert.value) return undefined

	return _pick(resolvedAlert.value, [
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
	if (!resolvedAlert.value) return undefined

	return _pick(resolvedAlert.value, [
		"gl2_remote_ip",
		"gl2_source_node",
		"gl2_accounted_message_size",
		"gl2_remote_port",
		"gl2_source_input",
		"gl2_message_id"
	])
})
</script>
