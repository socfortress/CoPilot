<template>
	<div class="healthcheck-item flex flex-col gap-2 px-5 py-3" :class="`status-${alert.level}`">
		<div class="header-box flex justify-between">
			<div class="id">
				<span>#{{ alert.checkID }}</span>
			</div>
			<div class="time">
				{{ formatDate(alert.time) }}
			</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="content flex gap-3 items-center">
				<div class="level mt-1">
					<Icon :name="WarningIcon" :size="20" v-if="alert.level === InfluxDBAlertLevel.Crit" />
					<Icon :name="OKIcon" :size="20" v-else />
				</div>
				<div class="title grow">
					{{ alert.checkName }}
					<n-popover style="padding: 0">
						<template #trigger>
							<Icon :name="MoreIcon" class="relative top-0.5 ml-1" />
						</template>
						<n-input
							:value="alert.message"
							type="textarea"
							readonly
							placeholder="Message"
							:autosize="{
								minRows: 3,
								maxRows: 10
							}"
						/>
					</n-popover>
				</div>
			</div>
		</div>
		<div class="footer-box flex justify-end items-center gap-3">
			<div class="time">{{ formatDate(alert.time) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import "@/assets/scss/vuesjv-override.scss"
import { NPopover, NInput } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { InfluxDBAlertLevel, type InfluxDBAlert } from "@/types/healthchecks.d"

const { alert } = defineProps<{ alert: InfluxDBAlert }>()

const WarningIcon = "carbon:warning-alt-filled"
const OKIcon = "carbon:checkmark-filled"
const MoreIcon = "iconoir:more-horiz-circle"

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetime)
}
</script>

<style lang="scss" scoped>
.healthcheck-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}

		.time {
			color: var(--fg-secondary-color);
		}
	}

	.main-box {
		word-break: break-word;

		.level {
			color: var(--success-color);
		}
	}

	.footer-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		margin-top: 10px;
		display: none;

		.time {
			text-align: right;
			color: var(--fg-secondary-color);
		}
	}

	&.status- {
		&crit {
			border-color: var(--warning-color);

			.level {
				color: var(--warning-color);
			}
		}
	}

	@container (max-width: 450px) {
		.header-box {
			.time {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
