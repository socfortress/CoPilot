<template>
	<div class="flex grow flex-col items-start gap-2 p-5" role="alert">
		<p class="text-error text-sm">{{ message }}</p>
		<n-button size="small" secondary @click="emit('retry')">Try again</n-button>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"

defineProps<{
	message: string
}>()

const emit = defineEmits<{
	(e: "retry"): void
}>()
</script>
