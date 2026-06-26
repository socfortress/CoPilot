<template>
	<span class="inline-block size-2 shrink-0 rounded-full" :class="colorClass" />
</template>

<script setup lang="ts">
import { computed } from "vue"

export type DotVariant = "muted" | "success" | "info" | "warning" | "danger"

const { variant = "muted" } = defineProps<{
	variant?: DotVariant
}>()

const colorClass = computed(() => {
	switch (variant) {
		case "success":
			return "bg-success"
		case "info":
			return "bg-primary"
		case "warning":
			return "bg-warning"
		case "danger":
			return "bg-error"
		default:
			return "bg-(--border-color)"
	}
})
</script>

<script lang="ts">
/** Map hit-count buckets to activity dot intensity (excludes muted/zero). */
export function hitsToDotVariant(hits: number): Exclude<DotVariant, "muted"> {
	if (hits >= 10000) return "danger"
	if (hits >= 1000) return "warning"
	if (hits >= 100) return "info"
	return "success"
}
</script>
