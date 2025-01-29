<template>
	<div>
		<CardEntity :status="alert.level === InfluxDBAlertLevel.Crit ? 'warning' : undefined">
			<template #headerMain>#{{ alert.checkID }}</template>
			<template #headerExtra>{{ formatDate(alert.time) }}</template>
			<template #default>
				<div class="flex items-center gap-3">
					<div class="mt-1">
						<Icon
							v-if="alert.level === InfluxDBAlertLevel.Crit"
							:name="WarningIcon"
							:size="20"
							class="text-warning"
						/>
						<Icon v-else :name="OKIcon" :size="20" class="text-success" />
					</div>
					<div class="grow" v-html="message"></div>
				</div>
			</template>
		</CardEntity>
	</div>
</template>

<script setup lang="ts">
import type { InfluxDBAlert } from "@/types/healthchecks.d"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { InfluxDBAlertLevel } from "@/types/healthchecks.d"
import dayjs from "@/utils/dayjs"
import { computed } from "vue"

const { alert } = defineProps<{ alert: InfluxDBAlert }>()

const WarningIcon = "carbon:warning-alt-filled"
const OKIcon = "carbon:checkmark-filled"

const message = computed(() => {
	return alert.message.replace(/\n/g, " <span class='mx-1'>•</span> ")
})

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetime)
}
</script>
