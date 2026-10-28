<template>
	<div class="flex flex-col gap-2">
		<ReadOnlyNotice v-if="readOnly" />
		<div v-if="caseData.alerts?.length && !readOnly" class="flex items-center justify-end gap-2">
			<LinkAlert
				:case-id="caseData.id"
				size="small"
				secondary
				:label="$t('cases.caseAlerts.linkAlert')"
				@linked="handleAlertLinked"
			/>
		</div>
		<div v-if="caseData.alerts?.length" class="flex flex-col gap-2">
			<CardEntity v-for="alert in caseData.alerts" :key="alert.id" size="small" embedded>
				<template #header-main>#{{ alert.id }}</template>
				<template #header-extra>
					<Chip v-bind="statusTagProps(alert.status)">
						{{ workflowStatusLabel(alert.status).toUpperCase() }}
					</Chip>
				</template>
				<template #default>
					{{ alert.alert_name }}
				</template>
				<template #footer-main>
					{{ $t("cases.caseAlerts.created", { date: formatDate(alert.alert_creation_time, dFormats.datetime) }) }}
				</template>
				<template #footer-extra>
					<div class="flex flex-wrap items-center justify-end gap-2">
						<Chip
							v-if="alert.assigned_to"
							:value="alert.assigned_to"
							:label="$t('cases.caseAlerts.assignedTo')"
						/>
						<UnlinkCase
							v-if="!readOnly"
							:alert-id="alert.id"
							:case-id="caseData.id"
							size="small"
							:label="$t('cases.caseAlerts.unlinkAlert')"
							@unlinked="handleAlertUnlinked"
						/>
						<AlertDetailsButton :alert-id="alert.id" size="small" @status-updated="handleStatusUpdated" />
					</div>
				</template>
			</CardEntity>
		</div>

		<div v-else-if="caseData.alert_ids?.length" class="flex flex-wrap gap-2">
			<code v-for="alertId in caseData.alert_ids" :key="alertId">
				{{ $t("cases.caseAlerts.alertId", { id: alertId }) }}
			</code>
		</div>

		<n-empty v-else :description="$t('cases.caseAlerts.empty')" class="min-h-50 justify-center">
			<template v-if="!readOnly" #extra>
				<div class="flex items-center justify-center gap-2">
					<LinkAlert
						:case-id="caseData.id"
						size="small"
						secondary
						:label="$t('cases.caseAlerts.linkAlert')"
						@linked="handleAlertLinked"
					/>
				</div>
			</template>
		</n-empty>
	</div>
</template>

<script setup lang="ts">
import type { AlertStatusUpdateSuccessPayload } from "@/components/alerts/AlertStatusSelect.vue"
import type { Case } from "@/types/cases"
import { NEmpty } from "naive-ui"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import LinkAlert from "@/components/alerts/LinkAlert.vue"
import UnlinkCase from "@/components/cases/UnlinkCase.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import ReadOnlyNotice from "@/components/common/ReadOnlyNotice.vue"
import { useReadOnly } from "@/composables/common/useReadOnly"
import { useSettingsStore } from "@/stores/settings"
import { statusTagProps } from "@/utils"
import { formatDate } from "@/utils/format"
import { workflowStatusLabel } from "@/utils/workflowStatus"

const { caseData } = defineProps<{
	caseData: Case
}>()

const emit = defineEmits<{
	(e: "updated", value: number): void
	(e: "unlinked", value: number): void
	(e: "linked", value: number): void
}>()

// May only read this customer's data: no alert linked or unlinked (#1312).
const readOnly = useReadOnly(() => caseData.customer_code)

const dFormats = useSettingsStore().dateFormat

function handleStatusUpdated(payload: AlertStatusUpdateSuccessPayload) {
	emit("updated", payload.alertId)
}

function handleAlertUnlinked(alertId: number) {
	emit("unlinked", alertId)
}

function handleAlertLinked(alertId: number) {
	emit("linked", alertId)
}
</script>
