<template>
	<n-popover overlap placement="top-end" class="max-h-60" scrollable to="body" :disabled="hideTimeline">
		<template #trigger>
			<div
				class="text-secondary flex items-center gap-2 font-mono"
				:class="{ 'hover:text-primary cursor-help': !hideTimeline }"
			>
				<span>
					{{ formatDate(alert.alert_source_event_time) }}
				</span>
				<Icon v-if="!hideTimeline" :name="TimeIcon" :size="16" />
			</div>
		</template>
		<div class="flex flex-col px-1 py-2">
			<SocAlertItemTimeline :alert />
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert"
import { NPopover } from "naive-ui"
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import SocAlertItemTimeline from "./SocAlertItemTimeline.vue"

const props = defineProps<{
	alert: SocAlert
	hideTimeline?: boolean
}>()
const { alert, hideTimeline } = toRefs(props)

const TimeIcon = "carbon:time"

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}
</script>
