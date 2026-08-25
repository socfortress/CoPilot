<template>
	<div class="border-default flex flex-col overflow-hidden rounded-lg border">
		<div class="border-default bg-secondary border-b px-4 py-2">
			<span class="text-secondary text-xs font-medium">{{ title }}</span>
		</div>
		<div class="p-3">
			<CodeSource :code="code || emptyText" :max-height="400" />
		</div>
	</div>
</template>

<script setup lang="ts">
import CodeSource from "@/components/common/CodeSource.vue"

withDefaults(
	defineProps<{
		title: string
		code?: string
		emptyText?: string
	}>(),
	{ code: "", emptyText: "— nothing extracted —" }
)
</script>
