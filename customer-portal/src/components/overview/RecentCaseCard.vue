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
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardCase } from "./types"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getStatusColor } from "@/utils"
import { formatTimeAgo } from "@/utils/format"

defineProps<{
	caseData: DashboardCase
	embedded?: boolean
}>()

const dFormats = useSettingsStore().dateFormat
</script>
