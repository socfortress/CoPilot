<template>
	<div class="flex flex-col gap-2">
		<div v-for="item of list" :key="item.label" class="flex items-center justify-between gap-2 text-xs">
			<strong>{{ item.label }}</strong>
			<code class="text-xxs">
				{{ item.value }}
			</code>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	list: {
		label: string
		value: string | number | null
	}[]
}>()
</script>
