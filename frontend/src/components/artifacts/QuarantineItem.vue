<template>
	<CardEntity embedded>
		<template #header>
			{{ formatDate(quarantine.Time, dFormats.datetimesec) }}
		</template>
		<template #default>
			{{ quarantine.Result }}
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { QuarantineResult } from "@/types/artifacts.d"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const { quarantine } = defineProps<{ quarantine: QuarantineResult }>()

const dFormats = useSettingsStore().dateFormat
</script>
