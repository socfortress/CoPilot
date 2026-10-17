<template>
	<n-tooltip v-if="label" trigger="hover">
		<template #trigger>
			<span
				class="text-tertiary cursor-default font-mono text-xs"
				:class="{ 'text-warning': heavy }"
				data-testid="talon-v2-context"
			>
				{{ label }}
			</span>
		</template>
		Talon is carrying {{ tokens?.toLocaleString() }} tokens of this thread.
		{{
			heavy
				? "Replies get slower and more expensive as this grows: start a new thread to reset it."
				: "A new thread starts empty."
		}}
	</n-tooltip>
</template>

<script setup lang="ts">
// The thread's context size: the thread's `context_tokens`, or the last turn's `data-usage`.
import { NTooltip } from "naive-ui"
import { computed } from "vue"
import { contextLabel } from "@/api/talonV2Parser"

const { tokens } = defineProps<{ tokens?: number | null }>()

// Past roughly this size replies slow down, as in the v1 chat. Advisory, not a limit.
const HEAVY_CONTEXT_TOKENS = 300_000

const label = computed(() => contextLabel(tokens))
const heavy = computed(() => (tokens ?? 0) >= HEAVY_CONTEXT_TOKENS)
</script>
