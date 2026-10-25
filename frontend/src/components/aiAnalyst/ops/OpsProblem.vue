<template>
	<n-alert
		:type="state.kind === 'error' ? 'error' : 'info'"
		:bordered="false"
		:title="state.title"
		data-testid="talon-ops-problem"
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
					data-testid="talon-ops-retry"
					@click="emit('retry')"
				>
					Try again
				</n-button>
				<a
					v-if="state.kind !== 'error'"
					:href="OPS_DOCS"
					target="_blank"
					rel="noopener noreferrer"
					class="text-primary text-sm"
				>
					About Talon's ops jobs
				</a>
			</div>
		</div>
	</n-alert>
</template>

<script setup lang="ts">
// What an Ops section shows instead of its data: Talon v2 off, a Talon without the ops API, or a
// failure (CoPilot's fixed text, with a retry).
import type { OpsProblem as OpsProblemState } from "./ops"
import { NAlert, NButton } from "naive-ui"
import { OPS_DOCS } from "./ops"

const { state, retry = true } = defineProps<{ state: OpsProblemState; retry?: boolean }>()
const emit = defineEmits<{ (e: "retry"): void }>()
</script>
