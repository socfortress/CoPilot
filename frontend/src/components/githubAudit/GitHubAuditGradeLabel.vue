<template>
	<p
		v-if="grade"
		class="font-mono text-4xl leading-none font-bold tracking-tight"
		:class="gradeTextClass"
	>
		{{ grade }}
	</p>
	<p v-else class="text-tertiary font-mono text-3xl leading-none font-semibold">—</p>
</template>

<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{
	grade?: string | null
}>()

const gradeTextClass = computed(() => {
	const value = props.grade
	if (!value) return ""
	if (value === "A" || value === "A+") return "text-success"
	if (value.startsWith("B")) return "text-info"
	if (value.startsWith("C")) return "text-warning"
	if (value === "D" || value === "D+" || value === "F") return "text-error"
	return "text-tertiary"
})
</script>
