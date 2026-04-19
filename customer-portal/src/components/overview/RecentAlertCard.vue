<template>
	<CardEntity :embedded header-box-class="flex-nowrap!" header-main-box-class="truncate">
		<template #header-main>
			{{ alert.name }}
		</template>
		<template #header-extra>
			<Chip :type="getSeverityColor(alert.severity)" size="small">
				{{ alert.severity }}
			</Chip>
		</template>
		<template #default>
			{{ alert.description }}
		</template>
		<template #footer-main>
			{{ formatTimeAgo(alert.created_at, dFormats.datetime) }}
		</template>
		<template #footer-extra>
			<AlertDetailsButton :alert-id="alert.id" size="small" />
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardAlert } from "./types"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getSeverityColor } from "@/utils"
import { formatTimeAgo } from "@/utils/format"

defineProps<{
	alert: DashboardAlert
	embedded?: boolean
}>()

const dFormats = useSettingsStore().dateFormat
</script>
