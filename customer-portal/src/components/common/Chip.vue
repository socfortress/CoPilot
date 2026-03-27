<template>
	<n-tag
		class="max-w-full p-0! [&_.n-base-close]:ml-0! [&_.n-base-close]:w-5.5! [&_.n-tag\_\_content]:h-full [&_.n-tag\_\_content]:overflow-hidden"
		:size
		:clickable
		:type
		:class="{ clickable }"
	>
		<div
			class="divide-border flex h-full items-stretch divide-x *:flex *:items-center *:overflow-hidden *:px-2 *:py-0.5"
		>
			<slot />
		</div>
	</n-tag>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import { NTag } from "naive-ui"

const { size, clickable, type } = defineProps<{
	size?: TagProps["size"]
	clickable?: boolean
	type?: TagProps["type"]
}>()
</script>

<style lang="scss" scoped>
.clickable {
	cursor: pointer;

	:deep(.n-tag__content) {
		transition: color 0.2s var(--bezier-ease);
	}
	&:hover {
		:deep(.n-tag__content) {
			color: var(--primary-color);
		}
		:deep(.n-tag__border) {
			border-color: rgba(var(--primary-color-rgb) / 0.5);
		}
	}
}
</style>
