<template>
	<CardEntity
		size="small"
		embedded
		main-box-class="gap-2"
		header-box-class="flex-nowrap! items-start text-default!"
		:status="cardStatus"
	>
		<template #headerMain>
			<span class="line-clamp-2 text-sm leading-snug font-semibold" :title="alert.check_name">
				{{ alert.check_name }}
			</span>
		</template>

		<template #headerExtra>
			<Badge type="splitted" bright size="small" :color="severityBadgeColor">
				<template #label>
					<Icon :name="severityIcon" :size="12" />
					Severity
				</template>
				<template #value>{{ severityLabel }}</template>
			</Badge>
		</template>

		<template #default>
			<p class="text-secondary font-mono text-xs leading-relaxed" :title="alert.message">
				{{ formattedMessage }}
			</p>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge type="splitted" bright size="small" :color="alertStatusBadgeColor">
					<template #label>
						<Icon :name="alertStatusIcon" :size="12" />
						Status
					</template>
					<template #value>{{ alertStatusLabel }}</template>
				</Badge>
				<Badge v-if="alert.sensor_type" type="splitted" bright size="small">
					<template #label>Sensor</template>
					<template #value>{{ alert.sensor_type }}</template>
				</Badge>
				<Badge type="splitted" bright size="small">
					<template #label>Detected</template>
					<template #value>{{ formatDate(alert.time, dFormats.datetime, { utc: true }) }}</template>
				</Badge>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { InfluxDBAlert } from "@/types/healthchecks.d"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { InfluxDBAlertSeverity, InfluxDBAlertStatus } from "@/types/healthchecks.d"
import { formatDate } from "@/utils/format"

const { alert } = defineProps<{ alert: InfluxDBAlert }>()

const NEWLINE_REGEX = /\r?\n/g

const dFormats = useSettingsStore().dateFormat

const formattedMessage = computed(() => alert.message.replace(NEWLINE_REGEX, " • "))

const severityLabel = computed(() => {
	const labels: Record<InfluxDBAlertSeverity, string> = {
		[InfluxDBAlertSeverity.Critical]: "Critical",
		[InfluxDBAlertSeverity.Warning]: "Warning",
		[InfluxDBAlertSeverity.Info]: "Info",
		[InfluxDBAlertSeverity.Ok]: "OK"
	}
	return labels[alert.severity] ?? alert.severity
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

const severityBadgeColor = computed((): BadgeColor | undefined => {
	switch (alert.severity) {
		case InfluxDBAlertSeverity.Critical:
			return "danger"
		case InfluxDBAlertSeverity.Warning:
			return "warning"
		case InfluxDBAlertSeverity.Info:
			return "primary"
		default:
			return "success"
	}
})

const cardStatus = computed((): "error" | "warning" | undefined => {
	if (alert.severity === InfluxDBAlertSeverity.Critical) return "error"
	if (alert.severity === InfluxDBAlertSeverity.Warning) return "warning"
	return undefined
})

const alertStatusLabel = computed(() => (alert.status === InfluxDBAlertStatus.Active ? "Active" : "Cleared"))

const alertStatusIcon = computed(() =>
	alert.status === InfluxDBAlertStatus.Active ? "carbon:warning-filled" : "carbon:checkmark-filled"
)

const alertStatusBadgeColor = computed((): BadgeColor | undefined =>
	alert.status === InfluxDBAlertStatus.Active ? "danger" : "success"
)
</script>
