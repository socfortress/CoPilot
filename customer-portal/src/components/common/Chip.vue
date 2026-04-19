<template>
	<n-tag :size :type :bordered :round>
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

withDefaults(
	defineProps<{
		label?: string | number | null
		value?: string | number | null
		type?: TagProps["type"]
		size?: TagProps["size"]
		bordered?: boolean
		round?: boolean
	}>(),
	{
		bordered: true,
		round: false
	}
)
</script>
