<template>
	<div class="rounded-lg bg-white shadow-sm">
		<div class="border-b border-gray-200 px-6 py-4">
			<h3 class="text-lg font-medium text-gray-900">Recent Cases</h3>
		</div>
		<div class="p-6">
			<div v-if="recentCases.length === 0" class="py-8 text-center text-gray-500">
				No recent cases
			</div>
			<div v-else class="space-y-4">
				<div
					v-for="case_ in recentCases"
					:key="case_.id"
					class="flex items-start space-x-3 rounded-lg p-3 hover:bg-gray-50"
				>
					<div
						class="mt-2 h-3 w-3 rounded-full"
						:class="{
							'bg-red-500': case_.status === 'open',
							'bg-yellow-500': case_.status === 'in_progress',
							'bg-green-500': case_.status === 'closed'
						}"
					></div>
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-gray-900">
							{{ case_.name }}
						</p>
						<p class="truncate text-sm text-gray-500">
							{{ case_.description }}
						</p>
						<p class="mt-1 text-xs text-gray-400">
							{{ formatTimeAgo(case_.created_at, dFormats.datetime) }}
							<span v-if="case_.assigned_to">• Assigned to {{ case_.assigned_to }}</span>
						</p>
					</div>
					<span
						class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
						:class="{
							'bg-red-100 text-red-800': case_.status === 'open',
							'bg-yellow-100 text-yellow-800': case_.status === 'in_progress',
							'bg-green-100 text-green-800': case_.status === 'closed'
						}"
					>
						{{ case_.status }}
					</span>
				</div>
			</div>
			<div class="mt-6 text-center">
				<button class="text-sm font-medium text-indigo-600 hover:text-indigo-500" @click="emit('viewAll')">
					View all cases →
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import { formatTimeAgo } from "@/utils/format"

defineProps<{
	recentCases: {
		id: number
		name: string
		description: string
		status: string
		created_at: string
		assigned_to?: string | null
	}[]
}>()

const emit = defineEmits<{
	viewAll: []
}>()

const dFormats = useSettingsStore().dateFormat
</script>
