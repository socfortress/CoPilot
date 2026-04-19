<template>
	<n-card :hoverable="clickable" :class="{ 'group cursor-pointer': clickable }" size="small">
		<div class="flex flex-col gap-2">
			<div
				:class="{ 'group-hover:text-primary': clickable }"
				class="flex items-start justify-between gap-4 overflow-hidden transition-colors duration-300"
			>
				<div class="truncate">{{ title }}</div>
				<Icon v-if="clickable" :name="icon || 'carbon:arrow-up-right'" />
			</div>

			<div class="flex gap-1.5 font-mono text-sm">
				<strong>{{ value }}</strong>
				<span class="text-secondary">{{ label }}</span>
			</div>
			<n-progress type="line" :percentage :status="percentageStatus" :show-indicator="false" />
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { ProgressStatus } from "naive-ui"
import { NCard, NProgress } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	title: string
	label?: string
	value: number | string
	percentage: number
	percentageStatus?: ProgressStatus
	icon?: string
	clickable?: boolean
}>()
</script>
