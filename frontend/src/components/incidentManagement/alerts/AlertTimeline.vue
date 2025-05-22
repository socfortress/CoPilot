<template>
	<n-timeline>
		<n-timeline-item type="success" title="Creation time" :time="formatDateTime(alert.alert_creation_time)" />
		<n-timeline-item v-if="alert.time_closed" title="Time closed" :time="formatDateTime(alert.time_closed)" />
	</n-timeline>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import { NTimeline, NTimelineItem } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const { alert } = defineProps<{ alert: Alert }>()

const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: Date): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}
</script>
