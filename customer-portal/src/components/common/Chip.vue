<template>
	<n-tag :size :type>
		<div v-if="$slots.default">
			<slot />
		</div>
		<div v-else class="flex items-center gap-2">
			<slot name="label">
				<div v-if="label" class="text-secondary">{{ label }}</div>
			</slot>
			<slot name="value">
				<div v-if="value">{{ value }}</div>
			</slot>
		</div>
	</n-tag>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import { NTag } from "naive-ui"

defineProps<{
	label?: string | number
	value?: string | number
	type?: TagProps["type"]
	size?: TagProps["size"]
}>()
</script>
