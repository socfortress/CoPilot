<template>
	<div v-if="alert.linked_cases?.length" class="flex flex-col gap-2">
		<CardEntity v-for="linkedCase in alert.linked_cases" :key="linkedCase.id" size="small" embedded>
			<template #header-main>#{{ linkedCase.id }} - {{ linkedCase.case_name }}</template>
			<template #header-extra>
				<Chip :type="getStatusColor(linkedCase.case_status)">
					{{ linkedCase.case_status.replace("_", " ").toUpperCase() }}
				</Chip>
			</template>
			<template #default>
				{{ linkedCase.case_description }}
			</template>
			<template #footer-main>
				Created: {{ formatDate(linkedCase.case_creation_time, dFormats.datetime) }}
			</template>
			<template #footer-extra>
				<Chip v-if="linkedCase.assigned_to" :value="linkedCase.assigned_to" label="Assigned to" />
			</template>
		</CardEntity>
	</div>

	<div v-else-if="alert.case_ids?.length" class="flex flex-wrap gap-2">
		<code v-for="caseId in alert.case_ids" :key="caseId">Case #{{ caseId }}</code>
	</div>

	<n-empty v-else description="No linked cases found" class="min-h-50 justify-center" />
</template>

<script setup lang="ts">
import type { Alert } from "@/api/endpoints/alerts"
import { NEmpty } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"

defineProps<{
	alert: Alert
}>()

const dFormats = useSettingsStore().dateFormat
</script>
