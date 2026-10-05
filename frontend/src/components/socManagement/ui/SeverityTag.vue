<template>
	<span class="inline-flex items-center gap-1.5 text-xs whitespace-nowrap">
		<span class="severity-dot size-2 shrink-0 rounded-full" :style="{ backgroundColor: SEVERITY_TONE[severity] }" />
		<span class="text-default">{{ severity }}</span>
	</span>
</template>

<script setup lang="ts">
import type { Severity } from "@/types/soc-management"
import { SEVERITY_TONE } from "../utils"

const { severity } = defineProps<{ severity: Severity }>()
</script>
