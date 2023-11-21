<template>
	<div class="alert-details flex flex-col gap-2 px-5 py-4">
		<div class="header-box flex justify-between">
			<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
				<span>#{{ alert._id }}</span>
				<Icon :name="InfoIcon" :size="16"></Icon>
			</div>
			<div class="time">
				{{ formatDate(alert._source.timestamp_utc) }}
			</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="content">
				<div class="rule-description">{{ alert._source.rule_description }}</div>
				<div class="rule-groups">{{ alert._source.rule_groups }}</div>

				<div class="badges-box flex flex-wrap items-center gap-3">
					<!--
						<Badge type="cursor">
							<template #iconLeft>
								<Icon :name="InfoIcon" :size="14"></Icon>
							</template>
						</Badge>
					-->
					<Badge type="splitted">
						<template #iconLeft>
							<Icon :name="TargetIcon" :size="13" class="!opacity-80"></Icon>
						</template>
						<template #label>Fired times</template>
						<template #value>{{ alert._source.rule_firedtimes }}</template>
					</Badge>

					<Badge :type="alert._source.rule_mail ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="alert._source.rule_mail ? MailIcon : DisabledIcon" :size="14"></Icon>
						</template>
						<template #label>Rule mail</template>
					</Badge>

					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<Badge type="splitted" hint-cursor>
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
									@click="gotoAgentPage(alert._source.agent_id)"
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
								<code>{{ alert._source.agent_labels_customer }}</code>
							</div>
						</div>
					</n-popover>
					<Badge type="splitted">
						<template #label>syslog</template>
						<template #value>{{ alert._source.syslog_type }} / {{ alert._source.syslog_level }}</template>
					</Badge>
					<Badge type="splitted" class="hide-on-small">
						<template #label>manager</template>
						<template #value>{{ alert._source.manager_name }}</template>
					</Badge>
					<Badge type="splitted" class="hide-on-small">
						<template #label>decoder</template>
						<template #value>{{ alert._source.decoder_name }}</template>
					</Badge>
					<Badge type="splitted" class="hide-on-small">
						<template #label>source</template>
						<template #value>{{ alert._source.source }}</template>
					</Badge>
				</div>
			</div>
			<div class="actions-box flex flex-col justify-end" v-if="!hideActions">
				<n-button type="primary" secondary v-if="alertUrl" tag="a" :href="alertUrl" target="_blank">
					<template #icon><Icon :name="ViewIcon"></Icon></template>
					View Alert
				</n-button>
				<n-button :loading="loading" type="warning" secondary @click="createAlert()" v-else>
					<template #icon><Icon :name="DangerIcon"></Icon></template>
					Create SOC Alert
				</n-button>
			</div>
		</div>
		<div class="footer-box flex justify-between items-center gap-4">
			<div class="actions-box flex flex-col justify-end" v-if="!hideActions">
				<n-button
					type="primary"
					secondary
					size="small"
					v-if="alertUrl"
					tag="a"
					:href="alertUrl"
					target="_blank"
				>
					<template #icon><Icon :name="ViewIcon"></Icon></template>
					View Alert
				</n-button>
				<n-button :loading="loading" type="warning" secondary size="small" @click="createAlert()" v-else>
					<template #icon><Icon :name="DangerIcon"></Icon></template>
					Create SOC Alert
				</n-button>
			</div>

			<div class="time">{{ formatDate(alert._source.timestamp_utc) }}</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:title="`Alert: ${alert._id}`"
			:bordered="false"
			segmented
		>
			<SimpleJsonViewer class="vuesjv-override" :model-value="alert._source" :initialExpandedDepth="2" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NButton, NPopover, NModal } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import type { Alert } from "@/types/alerts.d"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/vuesjv-override.scss"
import { useRouter } from "vue-router"
import Api from "@/api"
import { onBeforeMount, ref } from "vue"
import { useMessage } from "naive-ui/lib"

const { alert, hideActions } = defineProps<{ alert: Alert; hideActions?: boolean }>()

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const DangerIcon = "majesticons:exclamation-line"
const DisabledIcon = "ph:minus-bold"
const MailIcon = "carbon:email"
const AgentIcon = "carbon:police"
const ViewIcon = "iconoir:eye-alt"
const LinkIcon = "carbon:launch"

const message = useMessage()
const router = useRouter()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const alertUrl = ref("")

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}

function gotoAgentPage(agentId: string) {
	router.push(`/agent/${agentId}`).catch(() => {})
}

function createAlert() {
	loading.value = true

	Api.alerts
		.create(alert._index, alert._id)
		.then(res => {
			if (res.data.success) {
				res.data.alert_url && (alertUrl.value = res.data.alert_url)
				message.success(res.data?.message || "SOC Alert created.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	alert._source.alert_url && (alertUrl.value = alert._source.alert_url)
})
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
			line-height: 1;

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
