<template>
	<div>
		<CardEntity :status="statusType">
			<template #headerMain>
				<div class="flex items-center gap-2">
					<span>{{ alert.check_name }}</span>
					<n-tag
						v-if="alert.status === InfluxDBAlertStatus.Active"
						type="error"
						size="small"
						:bordered="false"
					>
						Active
					</n-tag>
					<n-tag v-else type="success" size="small" :bordered="false">Cleared</n-tag>
				</div>
			</template>
			<template #headerExtra>
				<div class="flex items-center gap-2">
					<n-tag v-if="alert.severity" :type="severityTagType" size="small" :bordered="false">
						{{ alert.severity.toUpperCase() }}
					</n-tag>
					<span>{{ formatDate(alert.time) }}</span>
				</div>
			</template>
			<template #default>
				<div class="flex items-center gap-3">
					<div class="mt-1">
						<Icon :name="severityIcon" :size="20" :class="severityIconClass" />
					</div>
					<div class="grow">
						<div class="font-mono text-sm" v-html="formattedMessage"></div>
						<div v-if="alert.sensor_type" class="mt-1 text-xs opacity-50">
							Sensor: {{ alert.sensor_type }}
						</div>
					</div>
				</div>
			</template>
		</CardEntity>
	</div>
</template>

<script setup lang="ts">
import type { InfluxDBAlert } from "@/types/healthchecks.d"
import { NTag } from "naive-ui"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { InfluxDBAlertSeverity, InfluxDBAlertStatus } from "@/types/healthchecks.d"
import dayjs from "@/utils/dayjs"

const { alert } = defineProps<{ alert: InfluxDBAlert }>()

const formattedMessage = computed(() => {
	return alert.message.replace(/\r?\n/g, " <span class='mx-1'>•</span> ")
})

const statusType = computed(() => {
	if (alert.severity === InfluxDBAlertSeverity.Critical) {
		return "error"
	} else if (alert.severity === InfluxDBAlertSeverity.Warning) {
		return "warning"
	}
	return undefined
})

const severityTagType = computed(() => {
	switch (alert.severity) {
		case InfluxDBAlertSeverity.Critical:
			return "error"
		case InfluxDBAlertSeverity.Warning:
			return "warning"
		case InfluxDBAlertSeverity.Info:
			return "info"
		default:
			return "success"
	}
})

const severityIcon = computed(() => {
	switch (alert.severity) {
		case InfluxDBAlertSeverity.Critical:
			return "carbon:warning-alt-filled"
		case InfluxDBAlertSeverity.Warning:
			return "carbon:warning"
		case InfluxDBAlertSeverity.Info:
			return "carbon:information-filled"
		default:
			return "carbon:checkmark-filled"
	}
})

const severityIconClass = computed(() => {
	switch (alert.severity) {
		case InfluxDBAlertSeverity.Critical:
			return "text-error-500"
		case InfluxDBAlertSeverity.Warning:
			return "text-warning-500"
		case InfluxDBAlertSeverity.Info:
			return "text-info-500"
		default:
			return "text-success-500"
	}
})

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetime)
}
</script>
