<template>
	<div class="bg-body flex h-1.5 w-full gap-0.5 overflow-hidden rounded-full" role="img" :aria-label>
		<div
			v-for="segment of visibleSegments"
			:key="segment.key"
			class="h-full min-w-0.75 transition-all duration-500 ease-out motion-reduce:transition-none"
			:class="bgClass(segment.color)"
			:style="{ width: `${(segment.value / total) * 100}%` }"
		/>
	</div>
</template>

<script setup lang="ts">
import type { StatusSegment } from "./status"
import { computed } from "vue"
import { bgClass } from "./status"

const { segments } = defineProps<{
	segments: StatusSegment[]
}>()

const total = computed(() => segments.reduce((sum, segment) => sum + segment.value, 0))
const visibleSegments = computed(() => (total.value ? segments.filter(segment => segment.value > 0) : []))
const ariaLabel = computed(() => segments.map(segment => `${segment.value} ${segment.label}`).join(", "))
</script>
