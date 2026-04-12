<template>
	<div class="flex flex-col gap-4">
		<div class="grid grid-cols-1 gap-4 @xl:grid-cols-2">
			<n-card size="small">
				<template #header>
					<div class="text-secondary text-sm">Alert Name</div>
				</template>
				{{ alert.alert_name }}
			</n-card>
			<n-card size="small">
				<template #header>
					<div class="text-secondary text-sm">Status</div>
				</template>
				<n-tag :type="getStatusColor(alert.status)">
					{{ alert.status.replace("_", " ").toUpperCase() }}
				</n-tag>
			</n-card>
			<n-card size="small">
				<template #header>
					<div class="text-secondary text-sm">Source</div>
				</template>
				{{ alert.source }}
			</n-card>

			<n-card size="small">
				<template #header>
					<div class="text-secondary text-sm">Customer</div>
				</template>
				{{ alert.customer_code }}
			</n-card>

			<n-card size="small">
				<template #header>
					<div class="text-secondary text-sm">Created</div>
				</template>
				{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
			</n-card>

			<n-card v-if="alert.assigned_to" size="small">
				<template #header>
					<div class="text-secondary text-sm">Assigned To</div>
				</template>
				{{ alert.assigned_to }}
			</n-card>

			<n-card v-if="alert.alert_description" size="small" class="@xl:col-span-2">
				<template #header>
					<div class="text-secondary text-sm">Description</div>
				</template>
				{{ alert.alert_description }}
			</n-card>
		</div>

		<div v-if="alert.tags && alert.tags.length > 0">
			<label class="block text-sm font-medium text-gray-700">Tags</label>
			<div class="mt-1 flex flex-wrap gap-2">
				<span
					v-for="tag in alert.tags"
					:key="tag.id"
					class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
				>
					{{ tag.tag }}
				</span>
			</div>
		</div>

		<div v-else-if="alert.tag && alert.tag.length > 0">
			<label class="block text-sm font-medium text-gray-700">Tags</label>
			<div class="mt-1 flex flex-wrap gap-2">
				<span
					v-for="tag in alert.tag"
					:key="tag"
					class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
				>
					{{ tag }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/api/endpoints/alerts"
import { NCard, NTag } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"

defineProps<{
	alert: Alert
}>()

const dFormats = useSettingsStore().dateFormat
</script>
