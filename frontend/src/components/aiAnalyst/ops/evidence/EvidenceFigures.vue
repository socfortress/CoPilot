<template>
	<dl
		v-if="items.length"
		class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm"
		data-testid="talon-ops-evidence-figures"
	>
		<template v-for="item of items" :key="item.key">
			<dt class="text-secondary">{{ item.label }}</dt>
			<dd class="break-all" :title="item.title" :data-testid="`talon-ops-figure-${item.key}`">
				<bdi>{{ item.text }}</bdi>
			</dd>
		</template>
	</dl>
</template>

<script setup lang="ts">
// Key figures as a definition list: each value as text with its unit; a time's UTC form is its tooltip.
import type { Figure } from "./evidence"

const { items } = defineProps<{ items: Figure[] }>()
</script>
