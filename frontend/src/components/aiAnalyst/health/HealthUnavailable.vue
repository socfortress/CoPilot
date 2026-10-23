<template>
	<p class="text-tertiary inline-flex items-start gap-1.5 py-4 text-sm" data-testid="talon-health-unavailable">
		<Icon name="carbon:unavailable" :size="15" class="mt-0.5 shrink-0" />
		<span>
			Unavailable:
			<bdi>{{ text }}</bdi>
		</span>
	</p>
</template>

<script setup lang="ts">
// A dashboard section Talon couldn't fill, with the reason CoPilot gave (a fixed text).
import Icon from "@/components/common/Icon.vue"

const { text } = defineProps<{ text: string }>()
</script>
