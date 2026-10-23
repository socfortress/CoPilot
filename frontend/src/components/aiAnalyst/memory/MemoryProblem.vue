<template>
	<n-alert
		:type="state.kind === 'error' ? 'error' : state.kind === 'no_memory' ? 'default' : 'info'"
		:bordered="false"
		:title="state.title"
		data-testid="talon-memory-problem"
		:data-kind="state.kind"
	>
		<div class="flex flex-col gap-2">
			<span>
				<bdi>{{ state.text }}</bdi>
			</span>
			<div class="flex flex-wrap items-center gap-3">
				<n-button
					v-if="state.kind === 'error' && retry"
					size="tiny"
					secondary
					data-testid="talon-memory-retry"
					@click="emit('retry')"
				>
					Try again
				</n-button>
				<a
					v-if="state.kind !== 'error'"
					:href="MEMORY_DOCS"
					target="_blank"
					rel="noopener noreferrer"
					class="text-primary text-sm"
				>
					About Talon's memory
				</a>
			</div>
		</div>
	</n-alert>
</template>

<script setup lang="ts">
// What a Memory section shows instead of its data: Talon v2 off, a Talon without the memory API, or
// a failure (CoPilot's fixed text, with a retry).
import type { ProblemState } from "./memory"
import { NAlert, NButton } from "naive-ui"
import { MEMORY_DOCS } from "./memory"

const { state, retry = true } = defineProps<{ state: ProblemState; retry?: boolean }>()
const emit = defineEmits<{ (e: "retry"): void }>()
</script>
