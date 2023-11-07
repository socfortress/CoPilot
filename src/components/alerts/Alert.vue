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
						<div class="badge cursor">
							<Icon :name="InfoIcon" :size="14"></Icon>
						</div>
					-->
					<div class="badge splitted">
						<span class="flex items-center gap-2">
							<Icon :name="TargetIcon" :size="13" class="!opacity-80"></Icon>
							Fired times
						</span>
						<span class="font-mono">{{ alert._source.rule_firedtimes }}</span>
					</div>
					<div class="badge" :class="{ active: alert._source.rule_mail }">
						<span>Rule mail</span>
						<Icon :name="alert._source.rule_mail ? MailIcon : DisabledIcon" :size="14"></Icon>
					</div>
					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<div class="badge splitted cursor-help">
								<span class="flex items-center gap-2">
									<Icon :name="AgentIcon" :size="13" class="!opacity-80"></Icon>
									Agent
								</span>
								<span>{{ alert._source.agent_labels_customer }}</span>
							</div>
						</template>
						<div class="flex flex-col gap-1">
							<div class="box">
								agent_id:
								<code
									class="cursor-pointer text-primary-color"
									@click="gotoAgentPage(alert._source.agent_id)"
								>
									{{ alert._source.agent_id }}
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
					<div class="badge splitted">
						<span>syslog</span>
						<span>{{ alert._source.syslog_type }} / {{ alert._source.syslog_level }}</span>
					</div>
					<div class="badge splitted hide-on-small">
						<span>manager</span>
						<span>{{ alert._source.manager_name }}</span>
					</div>
					<div class="badge splitted hide-on-small">
						<span>decoder</span>
						<span>{{ alert._source.decoder_name }}</span>
					</div>
					<div class="badge splitted hide-on-small">
						<span>source</span>
						<span>{{ alert._source.source }}</span>
					</div>
				</div>
			</div>
			<div class="actions-box flex flex-col justify-end">
				<n-button :loading="loading" type="warning" secondary @click="createAlert()">
					<template #icon><Icon :name="DangerIcon"></Icon></template>
					Create SOC Alert
				</n-button>
			</div>
		</div>
		<div class="footer-box flex justify-between items-center gap-4">
			<div class="actions-box flex flex-col justify-end">
				<n-button :loading="loading" type="warning" secondary size="small" @click="createAlert()">
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
import type { Alert } from "@/types/alerts.d"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/vuesjv-override.scss"
import { useRouter } from "vue-router"
import Api from "@/api"
import { ref } from "vue"
import { useMessage } from "naive-ui/lib"

const { alert } = defineProps<{ alert: Alert }>()

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const DangerIcon = "majesticons:exclamation-line"
const DisabledIcon = "ph:minus-bold"
const MailIcon = "carbon:email"
const AgentIcon = "carbon:police"

const message = useMessage()
const router = useRouter()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

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

				.badge {
					border-radius: var(--border-radius);
					border: var(--border-small-100);
					display: flex;
					align-items: center;
					font-size: 14px;
					padding: 0px 6px;
					height: 26px;
					line-height: 1;
					gap: 6px;
					transition: all 0.3s var(--bezier-ease);

					span,
					i {
						opacity: 0.5;
					}

					&.active {
						color: var(--primary-color);
						background-color: var(--primary-005-color);

						span,
						i {
							opacity: 1;
						}

						border-color: var(--primary-color);
					}

					&.cursor {
						cursor: pointer;

						i {
							opacity: 1;
						}

						&:hover {
							color: var(--primary-color);
							border-color: var(--primary-color);
						}
					}

					&.splitted {
						padding: 0px;
						gap: 0;
						overflow: hidden;

						span {
							padding: 0px 8px;
							height: 100%;
							line-height: 24px;
							opacity: 1;

							&:first-child {
								border-right: var(--border-small-100);
								background-color: var(--primary-005-color);
							}
						}
					}
					&.default {
						span,
						i {
							opacity: 1;
						}
					}
				}
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
