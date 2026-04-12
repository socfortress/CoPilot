<template>
	<div v-if="caseData.alerts?.length" class="flex flex-col gap-2">
		<CardEntity v-for="alert in caseData.alerts" :key="alert.id" size="small" embedded>
			<template #header-main>#{{ alert.id }} - {{ alert.alert_name }}</template>
			<template #header-extra>
				<Chip :type="getStatusColor(alert.status)">
					{{ alert.status.replace("_", " ").toUpperCase() }}
				</Chip>
			</template>
			<template #default>
				{{ alert.alert_description }}
			</template>
			<template #footer-main>Created: {{ formatDate(alert.alert_creation_time, dFormats.datetime) }}</template>
			<template #footer-extra>
				<Chip v-if="alert.assigned_to" :value="alert.assigned_to" label="Assigned to" />
			</template>
		</CardEntity>
	</div>

	<div v-else-if="caseData.alert_ids?.length" class="flex flex-wrap gap-2">
		<code v-for="alertId in caseData.alert_ids" :key="alertId">Alert #{{ alertId }}</code>
	</div>

	<n-empty v-else description="No alerts found" class="min-h-50 justify-center" />
</template>

<script setup lang="ts">
// TODO-CP: add link to alert details
import type { Case } from "@/types/cases"
import { NEmpty } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"

defineProps<{
	caseData: Case
}>()

const dFormats = useSettingsStore().dateFormat
</script>
