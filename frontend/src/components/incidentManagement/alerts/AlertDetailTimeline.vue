<template>
	<n-spin :show="loading" class="min-h-48">
		<n-timeline class="mt-4">
			<n-timeline-item
				v-for="(item, $index) of timeline"
				:key="item._id"
				:type="$index === 0 ? 'success' : undefined"
				:line-type="$index === timeline.length - 2 ? 'dashed' : undefined"
				:time="formatDateTime(item._source.timestamp)"
				class="pb-4"
			>
				<AlertDetailTimelineItem :timeline-data="item" embedded class="-mt-3" />
			</n-timeline-item>
		</n-timeline>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertAsset, AlertTimeline } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NSpin, NTimeline, NTimelineItem, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import AlertDetailTimelineItem from "./AlertDetailTimelineItem.vue"

const { asset } = defineProps<{ asset: AlertAsset }>()

const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const message = useMessage()
const timeline = ref<AlertTimeline[]>([])

function formatDateTime(timestamp: Date | string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}

function getAlertTimeline() {
	loading.value = true

	Api.incidentManagement.alerts
		.getAlertTimeline(asset.index_id, asset.index_name)
		.then(res => {
			if (res.data.success) {
				timeline.value = res.data?.alert_timeline || []
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

onBeforeMount(() => {
	getAlertTimeline()
})
</script>
