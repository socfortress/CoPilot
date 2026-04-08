<template>
	<n-card
		title="Recent Alerts"
		segmented
		:content-class="`flex flex-col gap-4 overflow-hidden ${!recentAlerts.length ? 'items-center justify-center' : 'p-0!'}`"
	>
		<n-empty v-if="!recentAlerts.length" description="No recent alerts" />

		<n-scrollbar v-else class="flex grow" trigger="none">
			<div class="flex flex-col gap-4 p-4">
				<CardEntity v-for="alert in recentAlerts" :key="alert.id" embedded>
					<template #header-main>
						{{ alert.name }}
					</template>
					<template #header-extra>
						<n-tag :type="getSeverityColor(alert.severity)" size="small">
							{{ alert.severity }}
						</n-tag>
					</template>
					<template #default>
						{{ alert.description }}
					</template>
					<template #footer-main>
						{{ formatTimeAgo(alert.created_at, dFormats.datetime) }}
					</template>
				</CardEntity>
			</div>
		</n-scrollbar>

		<n-button :text="!!recentAlerts.length" class="mb-4!" @click="goToAlerts()">
			<template #icon>
				<Icon name="carbon:launch" />
			</template>
			View all alerts
		</n-button>
	</n-card>
</template>

<script setup lang="ts">
import { NButton, NCard, NEmpty, NScrollbar, NTag } from "naive-ui"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getSeverityColor } from "@/utils"
import { formatTimeAgo } from "@/utils/format"

export interface DashboardAlert {
	id: number
	name: string
	description: string
	severity: string
	created_at: string
}

const props = defineProps<{
	recentAlerts?: DashboardAlert[]
}>()

const mockDashboardAlerts: DashboardAlert[] = [
	{
		id: 1,
		name: "CPU usage spike",
		description: "CPU usage exceeded 90% for over 5 minutes.",
		severity: "high",
		created_at: "2026-04-08T08:30:00.000Z"
	},
	{
		id: 2,
		name: "Storage threshold warning",
		description: "Disk usage reached 75% on node eu-west-1.",
		severity: "medium",
		created_at: "2026-04-08T07:45:00.000Z"
	},
	{
		id: 3,
		name: "Scheduled backup completed",
		description: "Nightly backup finished successfully.",
		severity: "low",
		created_at: "2026-04-08T06:10:00.000Z"
	},
	{
		id: 3,
		name: "Scheduled backup completed",
		description: "Nightly backup finished successfully.",
		severity: "low",
		created_at: "2026-04-08T06:10:00.000Z"
	},
	{
		id: 3,
		name: "Scheduled backup completed",
		description: "Nightly backup finished successfully.",
		severity: "low",
		created_at: "2026-04-08T06:10:00.000Z"
	},
	{
		id: 3,
		name: "Scheduled backup completed",
		description: "Nightly backup finished successfully.",
		severity: "low",
		created_at: "2026-04-08T06:10:00.000Z"
	},
	{
		id: 3,
		name: "Scheduled backup completed",
		description: "Nightly backup finished successfully.",
		severity: "low",
		created_at: "2026-04-08T06:10:00.000Z"
	},
	{
		id: 3,
		name: "Scheduled backup completed",
		description: "Nightly backup finished successfully.",
		severity: "low",
		created_at: "2026-04-08T06:10:00.000Z"
	},
	{
		id: 3,
		name: "Scheduled backup completed",
		description: "Nightly backup finished successfully.",
		severity: "low",
		created_at: "2026-04-08T06:10:00.000Z"
	}
]

const recentAlerts = computed(() => mockDashboardAlerts)

const dFormats = useSettingsStore().dateFormat
const { routeAlertsList } = useNavigation()

function goToAlerts() {
	routeAlertsList().navigate()
}
</script>
