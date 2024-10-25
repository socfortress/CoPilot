<template>
	<CardEntity>
		<div class="flex flex-col gap-1">
			<p>
				{{ artifact.name }}
			</p>
			{{ artifact.description }}
		</div>
	</CardEntity>
</template>

<script setup lang="ts">
import type { Artifact } from "@/types/artifacts.d"
import CardEntity from "@/components/common/cards/CardEntity.vue"

const { artifact } = defineProps<{ artifact: Artifact }>()
</script>
