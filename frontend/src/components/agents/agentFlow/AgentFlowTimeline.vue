<template>
	<n-timeline>
		<n-timeline-item type="success" title="Start" :time="formatDateTime(flow.start_time)" />
		<n-timeline-item
			v-if="flow.create_time"
			title="Create"
			:time="formatDateTime(flow.create_time)"
			line-type="dashed"
		/>
		<n-timeline-item v-if="flow.active_time" title="Active" :time="formatDateTime(flow.active_time)" />
	</n-timeline>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NTimeline, NTimelineItem } from "naive-ui"
import type { FlowResult } from "@/types/flow.d"

const { flow } = defineProps<{ flow: FlowResult }>()

const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: number): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}
</script>
