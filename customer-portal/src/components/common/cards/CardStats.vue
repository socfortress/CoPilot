<template>
	<n-card size="small" :class="{ 'group cursor-pointer': clickable }" :hoverable>
		<div class="flex flex-col gap-2">
			<div class="flex items-center justify-between gap-2">
				<span
					class="text-secondary text-sm transition-colors"
					:class="{ 'group-hover:text-primary': clickable }"
				>
					<slot name="title">{{ title }}</slot>
				</span>
				<Icon
					v-if="clickable"
					name="carbon:arrow-up-right"
					class="group-hover:text-primary transition-colors"
				/>
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

defineProps<{
	title?: string | number
	value?: string | number
	subtitle?: string | number
	hoverable?: boolean
	clickable?: boolean
}>()
</script>
