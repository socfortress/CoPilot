<template>
	<div class="item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="id">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="flex cursor-help items-center gap-2">
							<span>#{{ alertsEvent.event.id }}</span>
							<Icon :name="InfoIcon" :size="16"></Icon>
						</div>
					</template>
					<div class="flex flex-col gap-1">
						<div class="box">
							event_definition_id:
							<code
								class="text-primary-color cursor-pointer"
								@click="gotoEventsPage(alertsEvent.event.event_definition_id)"
							>
								{{ alertsEvent.event.event_definition_id }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
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
							<code class="text-primary-color cursor-pointer" @click="gotoIndex(alertsEvent.index_name)">
								{{ alertsEvent.index_name }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</div>
						<div class="box">
							index_type:
							<code>{{ alertsEvent.index_type }}</code>
						</div>
						<div class="box">
							timestamp:
							<code>{{ formatDateTime(alertsEvent.event.timestamp) }}</code>
						</div>
						<div class="box">
							timestamp processing:
							<code>{{ formatDateTime(alertsEvent.event.timestamp_processing) }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="time">
				<n-popover overlap placement="top-end">
					<template #trigger>
						<div class="flex cursor-help items-center gap-2">
							<span>
								{{ formatDateTime(alertsEvent.event.timestamp) }}
							</span>
							<Icon :name="TimeIcon" :size="16"></Icon>
						</div>
					</template>
					<div class="flex flex-col px-1 py-2">
						<n-timeline>
							<n-timeline-item
								type="success"
								title="Timestamp"
								:time="formatDateTime(alertsEvent.event.timestamp)"
							/>
							<n-timeline-item
								v-if="alertsEvent.event.timestamp_processing"
								title="Processing"
								:time="formatDateTime(alertsEvent.event.timestamp_processing)"
							/>
						</n-timeline>
					</div>
				</n-popover>
			</div>
		</div>
		<div class="main-box">
			<div class="content">
				{{ alertsEvent.event.message }}
			</div>
		</div>
		<div class="footer-box flex items-center justify-end gap-3">
			<div class="time">
				{{ formatDateTime(alertsEvent.event.timestamp) }}
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AlertsEventElement } from "@/types/graylog/alerts.d"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NPopover, NTimeline, NTimelineItem } from "naive-ui"

const { alertsEvent } = defineProps<{ alertsEvent: AlertsEventElement }>()

const emit = defineEmits<{
	(e: "clickEvent", value: string): void
}>()

const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"

const dFormats = useSettingsStore().dateFormat
const { gotoIndex } = useGoto()

function formatDateTime(timestamp: string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
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
	border: var(--border-small-050);

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
