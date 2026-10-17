<template>
	<div v-if="parts.length" class="text-tertiary font-mono text-xs" data-testid="talon-v2-usage">
		{{ parts.join(" · ") }}
	</div>
</template>

<script setup lang="ts">
// A completed turn's usage (the stream's `data-usage` chunk). The cost is the ledger's decimal
// string as it came, never a float.
import type { TalonV2Usage } from "@/types/talonV2"
import { computed } from "vue"

const { usage } = defineProps<{ usage: TalonV2Usage }>()

function count(value: number | null | undefined, one: string, many: string): string | null {
	if (typeof value !== "number") return null
	return `${value.toLocaleString()} ${value === 1 ? one : many}`
}

const parts = computed(() =>
	[
		typeof usage.input_tokens === "number" ? `${usage.input_tokens.toLocaleString()} in` : null,
		typeof usage.output_tokens === "number" ? `${usage.output_tokens.toLocaleString()} out` : null,
		count(usage.requests, "request", "requests"),
		count(usage.tool_calls, "tool call", "tool calls"),
		typeof usage.cost_usd === "string" ? `$${usage.cost_usd}` : null
	].filter((part): part is string => !!part)
)
</script>
