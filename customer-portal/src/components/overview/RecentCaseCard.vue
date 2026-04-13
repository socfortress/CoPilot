<template>
	<CardEntity :embedded header-box-class="flex-nowrap!" header-main-box-class="truncate">
		<template #header-main>
			{{ caseData.name }}
		</template>
		<template #header-extra>
			<Chip :type="getStatusColor(caseData.status)" size="small">
				{{ caseData.status }}
			</Chip>
		</template>
		<template #default>
			{{ caseData.description }}
		</template>
		<template #footer-main>
			{{ formatTimeAgo(caseData.created_at, dFormats.datetime) }}
		</template>
		<template #footer-extra>
			<CaseDetailsButton :case-id="caseData.id" size="small" @status-updated="handleStatusUpdated" />
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { CaseStatusUpdateSuccessPayload } from "../cases/CaseStatusSelect.vue"
import type { DashboardCase } from "./types"
import CaseDetailsButton from "@/components/cases/CaseDetailsButton.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getStatusColor } from "@/utils"
import { formatTimeAgo } from "@/utils/format"

const props = defineProps<{
	caseData: DashboardCase
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "updated", value: DashboardCase): void
}>()

const dFormats = useSettingsStore().dateFormat

function handleStatusUpdated(payload: CaseStatusUpdateSuccessPayload) {
	emit("updated", { ...props.caseData, status: payload.status })
}
</script>
