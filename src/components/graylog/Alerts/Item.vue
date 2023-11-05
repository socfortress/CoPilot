<template>
	<div class="item flex flex-col mb-2 gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="id">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="flex items-center gap-2 cursor-help">
							<span>#{{ alertsEvent.event.id }}</span>
							<Icon :name="InfoIcon" :size="16"></Icon>
						</div>
					</template>
					<div class="flex flex-col gap-1">
						<div class="box">
							event_definition_id:
							<code
								class="cursor-pointer text-primary-color"
								@click="gotoEventsPage(alertsEvent.event.event_definition_id)"
							>
								{{ alertsEvent.event.event_definition_id }}
							</code>
						</div>
						<div class="box">
							event_definition_type:
							<code>{{ alertsEvent.event.event_definition_type }}</code>
						</div>
						<div class="box">
							source:
							<code>{{ alertsEvent.event.source }}</code>
						</div>
						<div class="box">
							index_name:
							<code
								class="cursor-pointer text-primary-color"
								@click="gotoIndicesPage(alertsEvent.index_name)"
							>
								{{ alertsEvent.index_name }}
							</code>
						</div>
						<div class="box">
							index_type:
							<code>{{ alertsEvent.index_type }}</code>
						</div>
						<div class="box">
							timestamp:
							<code>{{ formatDate(alertsEvent.event.timestamp) }}</code>
						</div>
						<div class="box">
							timestamp processing:
							<code>{{ formatDate(alertsEvent.event.timestamp_processing) }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="time">
				<n-popover overlap placement="bottom-end">
					<template #trigger>
						<div class="flex items-center gap-2 cursor-help">
							<span>
								{{ formatDate(alertsEvent.event.timestamp) }}
							</span>
							<Icon :name="TimeIcon" :size="16"></Icon>
						</div>
					</template>
					<div class="flex flex-col gap-1">
						<div class="box">
							timestamp:
							<code>{{ formatDate(alertsEvent.event.timestamp) }}</code>
						</div>
						<div class="box">
							timestamp processing:
							<code>{{ formatDate(alertsEvent.event.timestamp_processing) }}</code>
						</div>
					</div>
				</n-popover>
			</div>
		</div>
		<div class="main-box">
			<div class="content">{{ alertsEvent.event.message }}</div>
		</div>
		<div class="footer-box flex justify-end items-center gap-3">
			<div class="time">{{ formatDate(alertsEvent.event.timestamp) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type AlertsEventElement } from "@/types/graylog/alerts.d"
import { NPopover } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import Icon from "@/components/common/Icon.vue"
import { useRouter } from "vue-router"

const { alertsEvent } = defineProps<{ alertsEvent: AlertsEventElement }>()

const emit = defineEmits<{
	(e: "clickEvent", value: string): void
}>()

const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"

const router = useRouter()
const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}

function gotoIndicesPage(index: string) {
	router.push(`/indices?index_name=${index}`).catch(() => {})
}

function gotoEventsPage(event_definition_id: string) {
	emit("clickEvent", event_definition_id)
}
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);

			&:hover {
				color: var(--primary-color);
			}
		}
		.time {
			color: var(--fg-secondary-color);

			&:hover {
				color: var(--primary-color);
			}
		}

		.actionable {
			cursor: pointer;
			color: var(--primary-color);
		}
	}
	.main-box {
		.content {
			word-break: break-word;
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

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 650px) {
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
