<template>
	<CardEntity :embedded header-box-class="flex-nowrap!" header-main-box-class="truncate">
		<template #header-main>
			{{ alert.name }}
		</template>
		<template #header-extra>
			<Chip :type="getStatusColor(alert.status)" size="small">
				{{ alert.status }}
			</Chip>
		</template>
		<template #default>
			{{ alert.description }}
		</template>
		<template #footer-main>
			<div class="flex flex-wrap items-center gap-2">
				<span>{{ formatTimeAgo(alert.created_at, dFormats.datetime) }}</span>
				<Chip v-for="tag of alert.tags" :key="tag" size="tiny" round :bordered="false">
					{{ tag }}
				</Chip>
			</div>
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
import { getStatusColor } from "@/utils"
import { formatTimeAgo } from "@/utils/format"

defineProps<{
	alert: DashboardAlert
	embedded?: boolean
}>()

const dFormats = useSettingsStore().dateFormat
</script>
