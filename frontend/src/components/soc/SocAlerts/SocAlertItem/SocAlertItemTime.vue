<template>
	<n-popover overlap placement="top-end" style="max-height: 240px" scrollable to="body" :disabled="hideTimeline">
		<template #trigger>
			<div class="time flex items-center gap-2" :class="{ hover: !hideTimeline }">
				<span>
					{{ formatDate(alert.alert_source_event_time) }}
				</span>
				<Icon v-if="!hideTimeline" :name="TimeIcon" :size="16" />
			</div>
		</template>
		<div class="flex flex-col px-1 py-2">
			<SocAlertItemTimeline :alert="alert" />
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
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

<style lang="scss" scoped>
.time {
	color: var(--fg-secondary-color);
	font-family: var(--font-family-mono);

	&.hover {
		cursor: help;

		&:hover {
			color: var(--primary-color);
		}
	}
}
</style>
