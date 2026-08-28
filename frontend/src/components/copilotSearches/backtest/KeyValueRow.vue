<template>
	<div
		class="border-default grid grid-cols-[minmax(140px,240px)_minmax(0,1fr)] items-start gap-3 border-b py-1.5 last:border-b-0"
		title="Click the value to copy"
		@click="emit('copy', value)"
	>
		<code class="text-tertiary text-xs break-all">{{ field }}</code>
		<span class="font-mono text-[13px] break-words whitespace-pre-wrap select-text">{{ value }}</span>
	</div>
</template>

<script setup lang="ts">
defineProps<{ field: string; value: string }>()
const emit = defineEmits<{ (e: "copy", value: string): void }>()
</script>
