<template>
	<div class="flex flex-col gap-4">
		<div class="grid grid-cols-1 gap-4 @xl:grid-cols-2">
			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">{{ $t("cases.caseOverview.caseName") }}</div>
				</template>
				{{ caseData.case_name }}
			</CardEntity>
			<CardEntity size="small">
				<template #header-main>
					<div class="text-secondary text-sm">{{ $t("common.fields.status") }}</div>
				</template>
				<template #header-extra>
					<Chip
						v-if="caseData.escalated"
						type="error"
						:value="$t('cases.caseOverview.escalated')"
						size="tiny"
						round
						:bordered="false"
					/>
				</template>
				<CaseStatusSelect
					:case-id="caseData.id"
					:status="caseData.case_status"
					@success="handleStatusUpdateSuccess"
				/>
			</CardEntity>
			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">{{ $t("cases.caseOverview.notificationInvokedNumber") }}</div>
				</template>
				{{ caseData.notification_invoked_number }}
			</CardEntity>

			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">{{ $t("common.fields.customer") }}</div>
				</template>
				<CustomerName :code="caseData.customer_code" />
			</CardEntity>

			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">{{ $t("common.fields.created") }}</div>
				</template>
				{{ formatDate(caseData.case_creation_time, dFormats.datetime) }}
			</CardEntity>

			<CardEntity size="small">
				<template #header>
					<div class="text-secondary text-sm">{{ $t("cases.caseOverview.assignedTo") }}</div>
				</template>
				<CaseAssignedSelect
					:case-id="caseData.id"
					:assigned-to="caseData.assigned_to"
					@success="handleAssignedToUpdateSuccess"
				/>
			</CardEntity>

			<CardEntity v-if="caseData.case_description" size="small" class="@xl:col-span-2">
				<template #header>
					<div class="text-secondary text-sm">{{ $t("common.fields.description") }}</div>
				</template>
				{{ caseData.case_description }}
			</CardEntity>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CaseAssignedUpdateSuccessPayload } from "../CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "../CaseStatusSelect.vue"
import type { Case } from "@/types/cases"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import CustomerName from "@/components/common/CustomerName.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import CaseAssignedSelect from "../CaseAssignedSelect.vue"
import CaseStatusSelect from "../CaseStatusSelect.vue"

defineProps<{
	caseData: Case
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: CaseStatusUpdateSuccessPayload): void
	(e: "assignedToUpdated", value: CaseAssignedUpdateSuccessPayload): void
}>()

const dFormats = useSettingsStore().dateFormat

function handleStatusUpdateSuccess(payload: CaseStatusUpdateSuccessPayload) {
	emit("statusUpdated", payload)
}

function handleAssignedToUpdateSuccess(payload: CaseAssignedUpdateSuccessPayload) {
	emit("assignedToUpdated", payload)
}
</script>
