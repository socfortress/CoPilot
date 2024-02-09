<template>
	<n-timeline>
		<n-timeline-item
			v-for="(item, $index) of history"
			:type="$index === 0 ? 'success' : undefined"
			:key="item.label"
			:title="item.label"
			:time="item.timeString"
			:line-type="$index === history.length - 2 ? 'dashed' : undefined"
		/>
	</n-timeline>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { onBeforeMount, ref } from "vue"
import type { SocNote } from "@/types/soc/note.d"
import { NTimeline, NTimelineItem } from "naive-ui"

const { note } = defineProps<{ note: SocNote }>()

const dFormats = useSettingsStore().dateFormat

const history = ref<
	{
		timeString: string
		label: string
	}[]
>([])

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}

onBeforeMount(() => {
	if (note.note_details.note_creationdate) {
		history.value.push({
			timeString: formatDate(note.note_details.note_creationdate, false),
			label: "Created"
		})
	}
	if (note.note_details.note_lastupdate) {
		history.value.push({
			timeString: formatDate(note.note_details.note_lastupdate, false),
			label: "Updated"
		})
	}
})
</script>
