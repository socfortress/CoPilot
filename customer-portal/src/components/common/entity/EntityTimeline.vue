<template>
	<n-card :title segmented :size>
		<n-timeline class="mt-2">
			<n-timeline-item
				v-for="item in timelineItems"
				:key="item.title"
				:title="item.title"
				:time="`${formatDate(item.date, dFormats[format])}`"
			/>
		</n-timeline>
	</n-card>
</template>

<script setup lang="ts">
import type { CardProps } from "naive-ui"
import { NCard, NTimeline, NTimelineItem } from "naive-ui"
import { computed } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { isDate } from "@/utils"
import { formatDate } from "@/utils/format"

export interface TimelineItem {
	title: string
	date?: string | Date | number | null
}

const {
	title = "Timeline",
	size = "small",
	items,
	format = "datetime"
} = defineProps<{
	title?: string
	size?: CardProps["size"]
	items: TimelineItem[]
	format?: "datetime" | "date" | "time" | "timesec" | "datetimesec"
}>()

const dFormats = useSettingsStore().dateFormat

const timelineItems = computed(() => {
	const filteredItems = items.filter(item => item.date && `${item.date}`.trim() && isDate(item.date))
	const mappedItems = filteredItems.map(item => ({ title: item.title, date: formatDate(`${item.date}`, "x") }))
	const sortedItems = mappedItems.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
	return sortedItems
})
</script>
