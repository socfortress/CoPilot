<template>
	<n-card
		size="small"
		:class="{ 'group cursor-pointer': clickable }"
		:hoverable
		content-class="flex items-center gap-4"
	>
		<div
			v-if="iconLeft"
			class="flex size-12 shrink-0 items-center justify-center rounded-sm p-1"
			:class="{
				'bg-warning/10 text-warning': color === 'warning',
				'bg-success/10 text-success': color === 'success',
				'bg-error/10 text-error': color === 'danger',
				'bg-primary/10 text-primary': color === 'primary',
				'bg-secondary text-secondary': !color
			}"
		>
			<Icon :name="iconLeft" :size="26" />
		</div>
		<div class="flex grow flex-col" :class="{ 'gap-1': size === 'small', 'gap-2': size === 'medium' }">
			<div class="flex items-center justify-between gap-2">
				<span
					class="text-secondary transition-colors"
					:class="{
						'group-hover:text-primary': clickable,
						'text-xs uppercase': size === 'small',
						'text-sm': size === 'medium'
					}"
				>
					<slot name="title">{{ title }}</slot>
				</span>
				<Icon
					v-if="clickable"
					:name="icon || 'carbon:arrow-up-right'"
					class="group-hover:text-primary transition-colors"
				/>
				<Icon v-else-if="icon" :name="icon" />
				<slot name="header-extra" />
			</div>
			<slot />
			<div class="font-mono text-xl font-semibold">
				<slot name="value">{{ value }}</slot>
			</div>
			<div v-if="subtitle || $slots.subtitle" class="text-secondary text-xs">
				<slot name="subtitle">{{ subtitle }}</slot>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

withDefaults(
	defineProps<{
		title?: string | number
		value?: string | number
		subtitle?: string | number
		hoverable?: boolean
		clickable?: boolean
		icon?: string
		iconLeft?: string
		size?: "small" | "medium"
		color?: "warning" | "success" | "danger" | "primary"
	}>(),
	{
		size: "medium"
	}
)
</script>
