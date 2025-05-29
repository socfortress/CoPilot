<template>
	<div class="divide-border flex flex-col gap-4 divide-y-2">
		<div v-for="reference of references" :key="reference.url" class="flex flex-col gap-0.5 pb-1 text-sm">
			<div>{{ reference.source }}</div>
			<div class="text-secondary text-xs">{{ reference.description }}</div>
			<div>
				<a :href="reference.url" target="_blank" rel="nofollow noopener noreferrer">
					{{ reference.url }}
				</a>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MitreReference } from "@/types/mitre.d"

const { references } = defineProps<{
	references: MitreReference[]
}>()
</script>
