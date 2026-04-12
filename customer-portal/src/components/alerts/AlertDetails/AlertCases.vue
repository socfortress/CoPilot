<template>
	<div v-if="alert.linked_cases?.length">
		<div
			v-for="linkedCase in alert.linked_cases"
			:key="linkedCase.id"
			class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
		>
			<div class="flex items-start justify-between">
				<div class="flex-1">
					<h4 class="text-sm font-medium text-gray-900">{{ linkedCase.case_name }}</h4>
					<p class="mt-1 text-xs text-gray-600">{{ linkedCase.case_description }}</p>
					<div class="mt-2 flex items-center space-x-4 text-xs text-gray-500">
						<span>Case #{{ linkedCase.id }}</span>
						<span>
							Created:
							{{ formatDate(linkedCase.case_creation_time, dFormats.datetime) }}
						</span>
						<span v-if="linkedCase.assigned_to">Assigned to: {{ linkedCase.assigned_to }}</span>
					</div>
				</div>
				<span
					class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium"
					:class="{
						'bg-red-100 text-red-800': linkedCase.case_status === 'OPEN',
						'bg-yellow-100 text-yellow-800': linkedCase.case_status === 'IN_PROGRESS',
						'bg-green-100 text-green-800': linkedCase.case_status === 'CLOSED'
					}"
				>
					{{ linkedCase.case_status.replace("_", " ").toUpperCase() }}
				</span>
			</div>
		</div>
	</div>

	<div v-else-if="alert.case_ids?.length">
		<span
			v-for="caseId in alert.case_ids"
			:key="caseId"
			class="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800"
		>
			Case #{{ caseId }}
		</span>
	</div>

	<n-empty v-else description="No linked cases found" class="min-h-50 justify-center" />
</template>

<script setup lang="ts">
import type { Alert } from "@/api/endpoints/alerts"
import { NEmpty } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

defineProps<{
	alert: Alert
}>()

const dFormats = useSettingsStore().dateFormat
</script>
