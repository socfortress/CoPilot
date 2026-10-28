<template>
	<time v-if="parts" :datetime="iso ?? undefined" :title="parts.utc" data-testid="talon-ops-time">
		{{ parts.local }}<template v-if="relative"> ({{ parts.relative }})</template>
	</time>
	<span v-else class="text-tertiary">—</span>
</template>

<script setup lang="ts">
// A time from the evidence: local time, the relative time beside it, the UTC time as the tooltip.
import { computed } from "vue"
import { timeParts } from "./evidence"

const { iso, relative = true } = defineProps<{ iso: string | null | undefined; relative?: boolean }>()
const parts = computed(() => timeParts(iso))
</script>
