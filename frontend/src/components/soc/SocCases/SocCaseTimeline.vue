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
import type { SocCaseExt } from "@/types/soc/case.d"
import _toNumber from "lodash/toSafeInteger"
import { NTimeline, NTimelineItem } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const { caseData } = defineProps<{ caseData: SocCaseExt }>()

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
	if (Object.keys(caseData.modification_history).length) {
		for (const key in caseData.modification_history) {
			const item = caseData.modification_history[key]
			history.value.push({
				timeString: formatDate(_toNumber(key) * 1000, false),
				label: `${item.action} [${item.user}]`
			})
		}
	}
})
</script>
