<template>
	<div class="flex flex-col gap-4">
		<div class="grid grid-cols-1 gap-4 @xl:grid-cols-2">
			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Case Name</div>
				</template>
				{{ caseData.case_name }}
			</CardEntity>
			<CardEntity size="small">
				<template #header-main>
					<div class="text-secondary text-sm">Status</div>
				</template>
				<template #header-extra>
					<Chip
						v-if="caseData.escalated"
						type="error"
						value="Escalated"
						size="tiny"
						round
						:bordered="false"
					/>
				</template>
				<Chip :type="getStatusColor(caseData.case_status)">
					{{ caseData.case_status.replace("_", " ").toUpperCase() }}
				</Chip>
			</CardEntity>
			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Notification Invoked Number</div>
				</template>
				{{ caseData.notification_invoked_number }}
			</CardEntity>

			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Customer</div>
				</template>
				{{ caseData.customer_code }}
			</CardEntity>

			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">Created</div>
				</template>
				{{ formatDate(caseData.case_creation_time, dFormats.datetime) }}
			</CardEntity>

			<CardEntity v-if="caseData.assigned_to" size="small">
				<template #header>
					<div class="text-secondary text-sm">Assigned To</div>
				</template>
				{{ caseData.assigned_to }}
			</CardEntity>

			<CardEntity v-if="caseData.case_description" size="small" class="@xl:col-span-2">
				<template #header>
					<div class="text-secondary text-sm">Description</div>
				</template>
				{{ caseData.case_description }}
			</CardEntity>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Case } from "@/types/cases"
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
