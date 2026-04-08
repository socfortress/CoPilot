<template>
	<CardEntity :embedded>
		<template #header-main>
			{{ caseData.name }}
		</template>
		<template #header-extra>
			<n-tag :type="getStatusColor(caseData.status)" size="small">
				{{ caseData.status }}
			</n-tag>
		</template>
		<template #default>
			{{ caseData.description }}
		</template>
		<template #footer-main>
			{{ formatTimeAgo(caseData.created_at, dFormats.datetime) }}
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardCase } from "./types"
import { NTag } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { getStatusColor } from "@/utils"
import { formatTimeAgo } from "@/utils/format"

defineProps<{
	caseData: DashboardCase
	embedded?: boolean
}>()

const dFormats = useSettingsStore().dateFormat
</script>
