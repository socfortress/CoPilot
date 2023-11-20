<template>
	<div class="artifact-item flex flex-col gap-1 px-5 py-3">
		<div class="name text-secondary-color">
			{{ artifact.name }}
		</div>
		<div class="description">{{ artifact.description }}</div>
	</div>
</template>

<script setup lang="ts">
import type { Artifact } from "@/types/artifacts.d"

const { artifact } = defineProps<{ artifact: Artifact }>()
</script>

<style lang="scss" scoped>
.artifact-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
}
</style>
