<template>
	<time
		class="text-secondary font-mono text-xs leading-4 whitespace-nowrap tabular-nums"
		:datetime="isoDate"
		:title="absolute"
	>
		{{ relative }}
	</time>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate, formatTimeAgo } from "@/utils/format"

/** "9 days ago" (or the date, past 30 days), with the full timestamp on hover. */
const { time } = defineProps<{
	time: string | Date
}>()

const dFormats = useSettingsStore().dateFormat

const relative = computed(() => formatTimeAgo(time, dFormats.datetime))
const absolute = computed(() => String(formatDate(time, dFormats.datetime)))
const isoDate = computed(() => {
	const date = new Date(time)
	return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
})
</script>
