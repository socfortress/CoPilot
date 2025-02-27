<template>
	<n-timeline>
		<n-timeline-item
			v-for="(item, $index) of history"
			:key="item.label"
			:type="$index === 0 ? 'success' : undefined"
			:title="item.label"
			:time="item.timeString"
			:line-type="$index === history.length - 2 ? 'dashed' : undefined"
		/>
	</n-timeline>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import _toNumber from "lodash/toSafeInteger"
import { NTimeline, NTimelineItem } from "naive-ui"
import { onBeforeMount, ref } from "vue"

const { alert } = defineProps<{ alert: SocAlert }>()

const dFormats = useSettingsStore().dateFormat

const history = ref<
	{
		timeString: string
		label: string
	}[]
>([])

function formatDate(timestamp: string | number, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}

onBeforeMount(() => {
	history.value.push({
		timeString: formatDate(alert.alert_source_event_time),
		label: "Source event"
	})

	if (Object.keys(alert.modification_history).length) {
		for (const key in alert.modification_history) {
			const item = alert.modification_history[key]
			history.value.push({
				timeString: formatDate(_toNumber(key) * 1000, false),
				label: `${item.action} [${item.user}]`
			})
		}
	}
})
</script>
