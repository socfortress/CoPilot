<template>
	<div class="alert-details flex flex-col gap-2 px-5 py-4">
		<div class="header-box flex justify-between">
			<div class="id flex items-center gap-2 cursor-pointer">
				<span>#{{ alert._id }}</span>
				<Icon :name="InfoIcon" :size="16"></Icon>
			</div>
			<div class="time">
				{{ formatDate(alert._source.timestamp_utc) }}
			</div>
		</div>
		<div class="main-box flex justify-between">
			<div class="content">
				<div class="rule-description">{{ alert._source.rule_description }}</div>
				<div class="rule-groups">{{ alert._source.rule_groups }}</div>

				<div class="badges-box flex flex-wrap items-center gap-3">
					<div class="badge cursor">
						<Icon :name="InfoIcon" :size="14"></Icon>
					</div>
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
					<div class="badge splitted">
						<span>{{ alert._source.syslog_type }}</span>
						<span>{{ alert._source.syslog_level }}</span>
					</div>
					<div class="badge splitted">
						<span class="flex items-center gap-2">
							<Icon :name="TargetIcon" :size="13" class="!opacity-80"></Icon>
							Agent
						</span>
						<span>{{ alert._source.agent_name }}</span>
					</div>
				</div>
			</div>
			<div class="actions-box flex flex-col justify-end">
				<n-button :loading="false" type="warning" secondary>
					<template #icon><Icon :name="DangerIcon"></Icon></template>
					Create SOC Alert
				</n-button>
			</div>
		</div>
		<div class="footer-box flex justify-between items-center">
			<div class="actions-box flex flex-col justify-end">
				<n-button :loading="false" type="warning" secondary size="small">
					<template #icon><Icon :name="DangerIcon"></Icon></template>
					Create SOC Alert
				</n-button>
			</div>

			<div class="time">{{ formatDate(alert._source.timestamp_utc) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import Icon from "@/components/common/Icon.vue"
import type { Alert } from "@/types/alerts.d"

const { alert } = defineProps<{ alert: Alert }>()

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const DangerIcon = "majesticons:exclamation-line"
const DisabledIcon = "ph:minus-bold"
const MailIcon = "carbon:email"

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}

/*
export interface AlertSource {
	agent_id: string
	agent_ip: AlertSourceAgentIP
	agent_name: string
	agent_labels_customer: string
	source: AlertSourceGl2RemoteIP
	streams: string[]
	decoder_name: AlertSourceDecoderName
	manager_name: string
	location: string
}
*/
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
				.badge {
					margin-top: 8px;
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
							}
							&:last-child {
								background-color: var(--bg-secondary-color);
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
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
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
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
