<template>
	<n-tag :type="tagType" size="small" round :bordered="false" class="text-xs font-semibold">
		{{ label }}
	</n-tag>
</template>

<script setup lang="ts">
import { NTag } from "naive-ui"
import { computed } from "vue"
import { PriorityLevel } from "@/types/patch-tuesday"

const props = defineProps<{
	priority: PriorityLevel | string
}>()

const tagType = computed(() => {
	switch (props.priority) {
		case PriorityLevel.P0:
			return "error"
		case PriorityLevel.P1:
			return "warning"
		case PriorityLevel.P2:
			return "info"
		case PriorityLevel.P3:
			return "success"
		default:
			return "default"
	}
})

const label = computed(() => {
	switch (props.priority) {
		case PriorityLevel.P0:
			return "P0"
		case PriorityLevel.P1:
			return "P1"
		case PriorityLevel.P2:
			return "P2"
		case PriorityLevel.P3:
			return "P3"
		default:
			return props.priority
	}
})
</script>
