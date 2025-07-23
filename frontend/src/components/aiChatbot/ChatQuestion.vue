<template>
	<div
		class="question bg-secondary ring-primary/20 flex w-max max-w-80 shrink-0 cursor-pointer flex-col gap-3 rounded-lg p-2 text-xs transition-all hover:ring-1"
	>
		<div>{{ entity.question }}</div>
		<div class="text-secondary description">
			<div>
				{{ entity.description }}
			</div>
		</div>
		<div>
			<n-tag size="small" class="[&_.n-tag\_\_content]:leading-0 text-[10px]! [&_.n-tag\_\_content]:p-0!">
				{{ entity.category }}
			</n-tag>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ExampleQuestion } from "@/types/copilotMCP.d"
import { NTag } from "naive-ui"

const { entity } = defineProps<{ entity: ExampleQuestion }>()
</script>

<style lang="scss" scoped>
.question {
	.description {
		display: grid;
		grid-template-rows: 0fr;
		opacity: 0;

		transition:
			opacity 0.3s var(--bezier-ease),
			grid-template-rows 0.3s var(--bezier-ease);

		& > * {
			overflow: hidden;
		}
	}
	&:hover {
		.description {
			grid-template-rows: 1fr;
			opacity: 1;
		}
	}
}
</style>
