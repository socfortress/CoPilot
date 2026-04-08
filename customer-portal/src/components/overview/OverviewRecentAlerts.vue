<template>
	<div class="rounded-lg bg-white shadow-sm">
		<div class="border-b border-gray-200 px-6 py-4">
			<h3 class="text-lg font-medium text-gray-900">Recent Alerts</h3>
		</div>
		<div class="p-6">
			<div v-if="recentAlerts.length === 0" class="py-8 text-center text-gray-500">No recent alerts</div>
			<div v-else class="space-y-4">
				<div
					v-for="alert in recentAlerts"
					:key="alert.id"
					class="flex items-start space-x-3 rounded-lg p-3 hover:bg-gray-50"
				>
					<div
						class="mt-2 h-3 w-3 rounded-full"
						:class="{
							'bg-red-500': alert.severity === 'high',
							'bg-yellow-500': alert.severity === 'medium',
							'bg-blue-500': alert.severity === 'low'
						}"
					></div>
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-gray-900">
							{{ alert.name }}
						</p>
						<p class="truncate text-sm text-gray-500">
							{{ alert.description }}
						</p>
						<p class="mt-1 text-xs text-gray-400">
							{{ formatTimeAgo(alert.created_at, dFormats.datetime) }}
						</p>
					</div>
					<span
						class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
						:class="{
							'bg-red-100 text-red-800': alert.severity === 'high',
							'bg-yellow-100 text-yellow-800': alert.severity === 'medium',
							'bg-blue-100 text-blue-800': alert.severity === 'low'
						}"
					>
						{{ alert.severity }}
					</span>
				</div>
			</div>
			<div class="mt-6 text-center">
				<button class="text-sm font-medium text-indigo-600 hover:text-indigo-500" @click="goToAlerts()">
					View all alerts →
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useNavigation } from "@/composables/common/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatTimeAgo } from "@/utils/format"

export interface DashboardAlert {
	id: number
	name: string
	description: string
	severity: string
	created_at: string
}

defineProps<{
	recentAlerts: DashboardAlert[]
}>()

const dFormats = useSettingsStore().dateFormat
const { routeAlertsList } = useNavigation()

function goToAlerts() {
	routeAlertsList().navigate()
}
</script>
