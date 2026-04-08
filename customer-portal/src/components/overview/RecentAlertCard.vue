<template>
	<CardEntity :embedded>
		<template #header-main>
			{{ alert.name }}
		</template>
		<template #header-extra>
			<n-tag :type="getSeverityColor(alert.severity)" size="small">
				{{ alert.severity }}
			</n-tag>
		</template>
		<template #default>
			{{ alert.description }}
		</template>
		<template #footer-main>
			{{ formatTimeAgo(alert.created_at, dFormats.datetime) }}
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardAlert } from "./types"
import { NTag } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { getSeverityColor } from "@/utils"
import { formatTimeAgo } from "@/utils/format"

defineProps<{
	alert: DashboardAlert
	embedded?: boolean
}>()

const dFormats = useSettingsStore().dateFormat
</script>
