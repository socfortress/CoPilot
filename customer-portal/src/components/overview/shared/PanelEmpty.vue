<template>
	<div class="flex grow flex-col items-center justify-center gap-1 p-8 text-center">
		<Icon :name="icon" :size="20" class="text-tertiary" />
		<p class="text-secondary text-sm">{{ text }}</p>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"

const { icon = "carbon:checkmark-outline" } = defineProps<{
	text: string
	icon?: string
}>()
</script>
