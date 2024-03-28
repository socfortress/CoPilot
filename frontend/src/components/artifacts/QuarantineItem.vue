<template>
	<div class="quarantine-item flex flex-col gap-1 px-5 py-3">
		<div class="time text-secondary-color">
			{{ formatDate(quarantine.Time, dFormats.datetimesec) }}
		</div>
		<div class="result">{{ quarantine.Result }}</div>
	</div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import type { QuarantineResult } from "@/types/artifacts.d"
import { formatDate } from "@/utils"

const { quarantine } = defineProps<{ quarantine: QuarantineResult }>()

const dFormats = useSettingsStore().dateFormat
</script>

<style lang="scss" scoped>
.quarantine-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
}
</style>
