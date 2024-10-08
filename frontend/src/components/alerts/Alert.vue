<template>
	<div class="alert-details flex flex-col gap-2 px-5 py-4">
		<div class="header-box flex justify-between">
			<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
				<span>#{{ alert._id || alert._source.id }}</span>
				<Icon :name="InfoIcon" :size="16"></Icon>
			</div>
			<div class="time">
				{{ formatDate(alert._source.timestamp_utc, dFormats.datetimesec) }}
			</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="content">
				<div class="rule-description">
					{{ alert._source.rule_description || alert._source.type }}
				</div>
				<div class="rule-groups">
					{{ alert._source.rule_groups }}
				</div>

				<div v-if="alert._id" class="badges-box flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TargetIcon" :size="13" class="!opacity-80"></Icon>
						</template>
						<template #label>Fired times</template>
						<template #value>
							{{ alert._source.rule_firedtimes }}
						</template>
					</Badge>

					<Badge :type="alert._source.rule_mail ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="alert._source.rule_mail ? MailIcon : DisabledIcon" :size="14"></Icon>
						</template>
						<template #label>Rule mail</template>
					</Badge>

					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<Badge type="splitted" color="primary" hint-cursor>
								<template #iconLeft>
									<Icon :name="AgentIcon" :size="13" class="!opacity-80"></Icon>
								</template>
								<template #label>Agent</template>
								<template #value>
									{{ alert._source.agent_name }} / {{ alert._source.agent_labels_customer }}
								</template>
							</Badge>
						</template>
						<div class="flex flex-col gap-1">
							<div class="box">
								agent_id:
								<code
									class="cursor-pointer text-primary-color"
									@click="gotoAgent(alert._source.agent_id)"
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
									class="cursor-pointer text-primary-color"
									@click="gotoCustomer({ code: alert._source.agent_labels_customer })"
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
					<Badge type="splitted" color="primary" class="hide-on-small">
						<template #label>manager</template>
						<template #value>
							{{ alert._source.manager_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="hide-on-small">
						<template #label>decoder</template>
						<template #value>
							{{ alert._source.decoder_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary" class="hide-on-small">
						<template #label>source</template>
						<template #value>
							{{ alert._source.source }}
						</template>
					</Badge>
				</div>
			</div>
			<AlertActions
				v-if="!hideActions"
				class="actions-box"
				:alert
				:soc-alert-field="socAlertCreationField"
				@start-loading="loading = true"
				@stop-loading="loading = false"
				@updated-url="alert._source.alert_url = $event"
				@updated-id="alert._source.alert_id = $event"
				@updated-ask-message="alert._source.ask_socfortress_message = $event"
			/>
		</div>
		<div class="footer-box flex justify-between items-center gap-4">
			<AlertActions
				v-if="!hideActions"
				class="actions-box"
				:alert
				:soc-alert-field="socAlertCreationField"
				size="small"
				@start-loading="loading = true"
				@stop-loading="loading = false"
				@updated-url="alert._source.alert_url = $event"
				@updated-id="alert._source.alert_id = $event"
				@updated-ask-message="alert._source.ask_socfortress_message = $event"
			/>
			<div class="time">
				{{ formatDate(alert._source.timestamp_utc, dFormats.datetimesec) }}
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Alert: ${alert._id || alert._source.id}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane v-if="alert._id" name="Agent" tab="Agent" display-directive="show">
					<div v-if="agentProperties" class="grid gap-2 grid-auto-fit-200 p-7 pt-4">
						<KVCard v-for="(value, key) of agentProperties" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								<template v-if="key === 'agent_id'">
									<code class="cursor-pointer text-primary-color" @click="gotoAgent(`${value}`)">
										{{ value }}
										<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
									</code>
								</template>
								<template v-else-if="key === 'agent_labels_customer'">
									<code
										class="cursor-pointer text-primary-color"
										@click="gotoCustomer(value ? { code: value.toString() } : undefined)"
									>
										{{ value }}
										<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
									</code>
								</template>
								<template v-else>
									{{ value || "-" }}
								</template>
							</template>
						</KVCard>
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
import type { Alert } from "@/types/alerts.d"
import type { SocAlertField } from "./type.d"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import _pick from "lodash/pick"
import { NInput, NModal, NPopover, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, inject, ref, toRefs } from "vue"

const props = defineProps<{ alert: Alert; hideActions?: boolean }>()
const AlertActions = defineAsyncComponent(() => import("./AlertActions.vue"))
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const { alert, hideActions } = toRefs(props)

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const DisabledIcon = "carbon:subtract"
const MailIcon = "carbon:email"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"

const { gotoCustomer, gotoAgent } = useGoto()
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

<style lang="scss" scoped>
.alert-details {
	transition: all 0.2s var(--bezier-ease);

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

			.rule-groups {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}

			.badges-box {
				margin-top: 16px;
			}
		}
	}
	.footer-box {
		display: none;
		font-size: 13px;
		margin-top: 10px;

		.time {
			font-family: var(--font-family-mono);
			color: var(--fg-secondary-color);
			text-align: right;
		}
	}

	&:hover {
		background-color: var(--primary-005-color);
	}

	@container (max-width: 650px) {
		.header-box {
			.time {
				display: none;
			}
		}
		.main-box {
			.actions-box {
				display: none;
			}

			.badges-box {
				.badge {
					&.hide-on-small {
						display: none;
					}
				}
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
