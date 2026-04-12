<template>
	<div class="flex flex-col gap-4">
		<div class="grid grid-cols-1 gap-4 @xl:grid-cols-2">
			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Alert Name</div>
				</template>
				{{ alert.alert_name }}
			</CardEntity>
			<CardEntity size="small">
				<template #header-main>
					<div class="text-secondary text-sm">Status</div>
				</template>
				<template #header-extra>
					<Chip v-if="alert.escalated" type="error" value="Escalated" size="tiny" round :bordered="false" />
				</template>
				<AlertStatusSelect
					:alert-id="alert.id"
					:status="alert.status"
					@success="handleStatusUpdateSuccess"
					@error="handleStatusUpdateError"
				/>
			</CardEntity>
			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Source</div>
				</template>
				{{ alert.source }}
			</CardEntity>

			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Customer</div>
				</template>
				{{ alert.customer_code }}
			</CardEntity>

			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Created</div>
				</template>
				{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
			</CardEntity>

			<CardEntity v-if="alert.assigned_to" size="small">
				<template #header>
					<div class="text-secondary text-sm">Assigned To</div>
				</template>
				{{ alert.assigned_to }}
			</CardEntity>

			<CardEntity v-if="alert.alert_description" size="small" class="@xl:col-span-2">
				<template #header>
					<div class="text-secondary text-sm">Description</div>
				</template>
				{{ alert.alert_description }}
			</CardEntity>
		</div>

		<div v-if="tags.length > 0" class="flex flex-wrap gap-2">
			<code v-for="tag in tags" :key="tag">#{{ tag }}</code>
		</div>
	</div>
</template>

<script setup lang="ts">
import type {
	AlertStatusUpdateErrorPayload,
	AlertStatusUpdateSuccessPayload
} from "@/components/alerts/AlertStatusSelect.vue"
import type { Alert } from "@/types/alerts"
import { useMessage } from "naive-ui"
import { computed } from "vue"
import AlertStatusSelect from "@/components/alerts/AlertStatusSelect.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	alert: Alert
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: AlertStatusUpdateSuccessPayload): void
}>()

const message = useMessage()

const dFormats = useSettingsStore().dateFormat

const tags = computed(() => {
	return [...(props.alert.tags?.map(tag => tag.tag) || []), ...(props.alert.tag || [])]
})

function handleStatusUpdateSuccess(payload: AlertStatusUpdateSuccessPayload) {
	emit("statusUpdated", { alertId: props.alert.id, status: payload.status })
}

function handleStatusUpdateError(payload: AlertStatusUpdateErrorPayload) {
	message.error(payload.message)
}
</script>
