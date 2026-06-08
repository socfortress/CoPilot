<template>
	<CardEntity
		size="small"
		embedded
		main-box-class="gap-2"
		header-box-class="flex-nowrap! items-start"
		:status="scheduleCardStatus(schedule)"
	>
		<template #headerMain>
			<span class="text-default line-clamp-2 text-sm leading-snug font-semibold">{{ schedule.name }}</span>
		</template>

		<template #headerExtra>
			<div class="flex shrink-0 items-center gap-2">
				<Badge
					v-if="schedule.last_execution_status"
					type="splitted"
					bright
					size="small"
					:color="lastExecutionBadgeColor(schedule.last_execution_status)"
				>
					<template #label>Status</template>
					<template #value>{{ lastExecutionStatusLabel(schedule.last_execution_status) }}</template>
				</Badge>
				<n-switch :value="schedule.enabled" size="small" @update:value="emit('toggle-enabled', $event)" />
			</div>
		</template>

		<template #default>
			<div class="text-secondary flex flex-col gap-1.5 text-xs">
				<div class="flex min-w-0 items-center gap-2">
					<span class="inline-flex shrink-0 items-center gap-1.5">
						<Icon :name="PatternIcon" :size="14" />
						<span class="text-tertiary font-medium uppercase">Index pattern</span>
					</span>
					<code class="truncate font-mono" :title="schedule.index_pattern">{{ schedule.index_pattern }}</code>
				</div>
				<div class="flex min-w-0 items-center gap-2">
					<span class="inline-flex shrink-0 items-center gap-1.5">
						<Icon :name="RepositoryIcon" :size="14" />
						<span class="text-tertiary font-medium uppercase">Repository</span>
					</span>
					<span class="truncate" :title="schedule.repository">{{ schedule.repository }}</span>
				</div>
			</div>
		</template>

		<template #mainExtra>
			<div class="flex flex-col gap-2">
				<span class="text-secondary text-[10px] font-medium tracking-wider uppercase">Configuration</span>
				<div class="flex flex-wrap gap-2">
					<Badge type="splitted" bright size="small" color="primary">
						<template #label>
							<Icon :name="ScheduleIcon" :size="12" />
							Schedule
						</template>
						<template #value>{{ formatScheduleLabel(schedule) }}</template>
					</Badge>
					<Badge type="splitted" size="small">
						<template #label>Timezone</template>
						<template #value>{{ schedule.timezone || "UTC" }}</template>
					</Badge>
					<Badge type="splitted" size="small">
						<template #label>Retention</template>
						<template #value>{{ formatRetention(schedule.retention_days) }}</template>
					</Badge>
					<Badge v-if="schedule.snapshot_prefix" type="splitted" size="small">
						<template #label>Prefix</template>
						<template #value>{{ schedule.snapshot_prefix }}</template>
					</Badge>
					<Badge v-if="schedule.include_global_state" type="splitted" size="small" color="primary">
						<template #label>Global state</template>
					</Badge>
					<Badge v-if="schedule.skip_write_indices" type="splitted" size="small" color="warning">
						<template #label>Skip write indices</template>
					</Badge>
				</div>
			</div>
		</template>

		<template v-if="showExecutionMeta" #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge v-if="schedule.last_execution_time" type="splitted" bright size="small">
					<template #label>
						<Icon :name="TimeIcon" :size="12" />
						Last run
					</template>
					<template #value>
						{{ formatDate(schedule.last_execution_time, "MMM D, YYYY HH:mm", { tz: true }) }}
					</template>
				</Badge>
				<Badge v-if="schedule.last_snapshot_name" type="splitted" size="small">
					<template #label>
						<Icon :name="SnapshotIcon" :size="12" />
						Last snapshot
					</template>
					<template #value>{{ schedule.last_snapshot_name }}</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex items-center gap-2">
				<n-button size="small" secondary @click="emit('edit')">
					<template #icon>
						<Icon :name="EditIcon" :size="14" />
					</template>
					Edit
				</n-button>
				<n-popconfirm @positive-click="emit('delete')">
					<template #trigger>
						<n-button size="small" type="error" secondary>
							<template #icon>
								<Icon :name="DeleteIcon" :size="14" />
							</template>
							Delete
						</n-button>
					</template>
					Are you sure you want to delete this schedule?
				</n-popconfirm>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { SnapshotScheduleResponse } from "@/types/snapshots.d"
import { NButton, NPopconfirm, NSwitch } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { formatDate } from "@/utils/format"

const { schedule } = defineProps<{
	schedule: SnapshotScheduleResponse
}>()

const emit = defineEmits<{
	"toggle-enabled": [enabled: boolean]
	edit: []
	delete: []
}>()

const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"
const PatternIcon = "carbon:code"
const RepositoryIcon = "carbon:datastore"
const ScheduleIcon = "carbon:calendar"
const TimeIcon = "carbon:time"
const SnapshotIcon = "carbon:camera"

const WEEKDAY_NAMES = [
	"Mondays",
	"Tuesdays",
	"Wednesdays",
	"Thursdays",
	"Fridays",
	"Saturdays",
	"Sundays"
] as const

const showExecutionMeta = computed(
	() => Boolean(schedule.last_execution_time || schedule.last_snapshot_name)
)

function formatRetention(retentionDays?: number | null) {
	return retentionDays ? `${retentionDays} days` : "Forever"
}

function formatScheduleCadence(scheduleItem: SnapshotScheduleResponse) {
	const interval = scheduleItem.interval_days ?? 1
	const dow = scheduleItem.day_of_week

	if (dow != null) {
		const dayLabel = WEEKDAY_NAMES[dow] ?? `Day ${dow}`
		return interval > 1 ? `${dayLabel} every ${interval} days` : dayLabel
	}

	return interval === 1 ? "Daily" : `Every ${interval} days`
}

function formatScheduleLabel(scheduleItem: SnapshotScheduleResponse) {
	const cadence = formatScheduleCadence(scheduleItem)

	if (scheduleItem.scheduled_hour == null) {
		return `${cadence} · Any hour`
	}

	const hourStr = String(scheduleItem.scheduled_hour).padStart(2, "0")
	const minStr = String(scheduleItem.scheduled_minute ?? 0).padStart(2, "0")
	return `${cadence} at ${hourStr}:${minStr}`
}

function lastExecutionBadgeColor(status?: string | null): BadgeColor | undefined {
	if (!status) return undefined
	if (status.startsWith("SUCCESS")) return "success"
	if (status.startsWith("SKIPPED") || status.startsWith("DEFERRED")) return "warning"
	return "danger"
}

function lastExecutionStatusLabel(status?: string | null) {
	return status?.split(":")[0] || "Unknown"
}

function scheduleCardStatus(scheduleItem: SnapshotScheduleResponse): "success" | "warning" | "error" | undefined {
	if (!scheduleItem.enabled) return "warning"
	const status = scheduleItem.last_execution_status
	if (!status) return undefined
	if (status.startsWith("SUCCESS")) return "success"
	if (status.startsWith("SKIPPED") || status.startsWith("DEFERRED")) return "warning"
	return "error"
}
</script>
