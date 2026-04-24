<template>
	<div class="flex items-center gap-3">
		<div class="w-16 shrink-0 text-sm">{{ label }}</div>
		<n-progress type="line" :percentage :show-indicator="false" :status="color" :height="10" class="grow" />
		<div class="text-secondary w-28 shrink-0 text-right text-sm">
			{{ count }} / {{ total }} ({{ percentage.toFixed(1) }}%)
		</div>
	</div>
</template>

<script setup lang="ts">
import { NProgress } from "naive-ui"
import { computed } from "vue"

const props = defineProps<{
	label: string
	count: number
	total: number
	color: "success" | "warning" | "error"
}>()

const percentage = computed(() => (props.total === 0 ? 0 : (props.count / props.total) * 100))
</script>
