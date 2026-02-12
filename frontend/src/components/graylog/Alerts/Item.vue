<template>
	<CardEntity>
		<template #headerMain>
			<n-popover overlap placement="bottom-start">
				<template #trigger>
					<div class="hover:text-primary flex cursor-help items-center gap-2">
						<span>#{{ alertsEvent.event.id }}</span>
						<Icon :name="InfoIcon" :size="16" />
					</div>
				</template>
				<div class="flex flex-col gap-1">
					<div class="box">
						event_definition_id:
						<code
							class="text-primary cursor-pointer"
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
						<code class="text-primary cursor-pointer" @click="routeIndex(alertsEvent.index_name)">
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
		</template>
		<template #headerExtra>
			<n-popover overlap placement="top-end">
				<template #trigger>
					<div class="hover:text-primary flex cursor-help items-center gap-2">
						<span>{{ formatDateTime(alertsEvent.event.timestamp) }}</span>
						<Icon :name="TimeIcon" :size="16" />
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
		</template>
		<template #default>{{ alertsEvent.event.message }}</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { AlertsEventElement } from "@/types/graylog/alerts.d"
import { NPopover, NTimeline, NTimelineItem } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const { alertsEvent } = defineProps<{ alertsEvent: AlertsEventElement }>()

const emit = defineEmits<{
	(e: "clickEvent", value: string): void
}>()

const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"

const dFormats = useSettingsStore().dateFormat
const { routeIndex } = useNavigation()

function formatDateTime(timestamp: string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}

function gotoEventsPage(event_definition_id: string) {
	emit("clickEvent", event_definition_id)
}
</script>
