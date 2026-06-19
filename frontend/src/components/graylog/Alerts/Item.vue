<template>
	<div>
		<CardEntity hoverable>
			<template #headerMain>
				<span>#{{ alertsEvent.event.id }}</span>
			</template>
			<template #headerExtra>
				<div class="flex items-center gap-2">
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
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="InfoIcon" />
						</template>
						Details
					</n-button>
				</div>
			</template>
			<template #default>{{ alertsEvent.event.message }}</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:title="`Alert #${alertsEvent.event.id}`"
			:bordered="false"
			segmented
		>
			<AlertsEventItemDetails :alerts-event @click-event="onClickEvent" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AlertsEventElement } from "@/types/graylog/alerts.d"
import { NButton, NModal, NPopover, NTimeline, NTimelineItem } from "naive-ui"
import { ref } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import AlertsEventItemDetails from "./AlertsEventItemDetails.vue"

const { alertsEvent } = defineProps<{ alertsEvent: AlertsEventElement }>()

const emit = defineEmits<{
	(e: "clickEvent", value: string): void
}>()

const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const showDetails = ref(false)

const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}

function onClickEvent(eventDefinitionId: string) {
	showDetails.value = false
	emit("clickEvent", eventDefinitionId)
}
</script>
