<template>
	<span
		class="target-cell inline-flex items-center gap-1.5 font-mono text-sm tabular-nums"
		:class="minutes == null ? 'text-tertiary' : 'text-default'"
		:title="minutes == null ? 'No target for this severity' : `Target: ${formatTarget(minutes)}`"
		data-testid="target-cell"
	>
		<Icon v-if="minutes != null" name="carbon:timer" :size="14" class="text-secondary shrink-0" />
		{{ minutes == null ? EMPTY : formatTarget(minutes) }}
	</span>
</template>

<script setup lang="ts">
// An SLA target in a table cell: the promise a row is measured against, legible at a
// glance (full ink, the size of the figures beside it) and plainly absent — a dash, not
// "no target" in small print — for a severity with no promise.
import Icon from "@/components/common/Icon.vue"
import { EMPTY, formatTarget } from "../utils"

const { minutes } = defineProps<{ minutes: number | null | undefined }>()
</script>
