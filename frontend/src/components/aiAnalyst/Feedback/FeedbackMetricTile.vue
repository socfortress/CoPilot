<template>
	<CardEntity size="small" embedded>
		<template #default>
			<div class="flex flex-col gap-1">
				<div class="text-secondary text-xs tracking-wide uppercase">{{ label }}</div>
				<div
					class="text-2xl font-semibold"
					:class="{
						'text-success': color === 'success',
						'text-warning': color === 'warning',
						'text-danger': color === 'danger'
					}"
				>
					{{ value }}
				</div>
				<div v-if="sub" class="text-secondary text-xs">{{ sub }}</div>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import CardEntity from "@/components/common/cards/CardEntity.vue"

defineProps<{
	label: string
	value: string
	sub?: string
	color?: "success" | "warning" | "danger"
}>()
</script>
