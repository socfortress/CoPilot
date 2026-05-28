<template>
	<n-tag :type="gradeType" :bordered="false" round :size>
		{{ grade }}
	</n-tag>
</template>

<script setup lang="ts">
import type { TagSize } from "naive-ui"
import { NTag } from "naive-ui"
import { computed } from "vue"

const props = defineProps<{
	grade: string
	size?: TagSize
	score?: number
}>()

const gradeType = computed(() => {
	switch (props.grade) {
		case "A":
		case "A+":
			return "success"
		case "B":
		case "B+":
			return "info"
		case "C":
		case "C+":
			return "warning"
		case "D":
		case "D+":
		case "F":
			return "error"
		default:
			return "default"
	}
})
</script>
