<template>
	<div class="status-bar bg-body flex h-1.5 w-full overflow-hidden rounded-full" role="img" :aria-label>
		<div
			v-for="segment of visibleSegments"
			:key="segment.key"
			class="segment h-full"
			:style="{ width: `${(segment.value / total) * 100}%`, backgroundColor: colorVar(segment.color) }"
		/>
	</div>
</template>

<script setup lang="ts">
import type { StatusSegment } from "./status"
import { computed } from "vue"
import { colorVar } from "./status"

const { segments } = defineProps<{
	segments: StatusSegment[]
}>()

const total = computed(() => segments.reduce((sum, segment) => sum + segment.value, 0))
const visibleSegments = computed(() => (total.value ? segments.filter(segment => segment.value > 0) : []))
const ariaLabel = computed(() => segments.map(segment => `${segment.value} ${segment.label}`).join(", "))
</script>

<style lang="scss" scoped>
.status-bar {
	gap: 2px;

	.segment {
		min-width: 3px;
		transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
	}
}

@media (prefers-reduced-motion: reduce) {
	.status-bar .segment {
		transition: none;
	}
}
</style>
