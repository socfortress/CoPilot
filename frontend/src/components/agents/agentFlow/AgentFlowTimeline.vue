<template>
	<n-timeline>
		<n-timeline-item type="success" title="Start" :time="formatDate(flow.start_time)" />
		<n-timeline-item
			v-if="flow.create_time"
			title="Create"
			:time="formatDate(flow.create_time)"
			line-type="dashed"
		/>
		<n-timeline-item v-if="flow.active_time" title="Active" :time="formatDate(flow.active_time)" />
	</n-timeline>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { NTimeline, NTimelineItem } from "naive-ui"
import type { FlowResult } from "@/types/flow.d"

const { flow } = defineProps<{ flow: FlowResult }>()

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: number): string {
	return dayjs(timestamp / 1000).format(dFormats.datetimesec)
}
</script>
