<template>
	<div class="flex items-stretch overflow-hidden rounded-lg border border-default bg-secondary">
		<div class="flex grow flex-col justify-center gap-1 border-r border-default px-5 py-4">
			<div
				v-if="summary.agent_name"
				class="agent"
				:class="{ 'text-secondary': summary.agent_name && summary.rule }"
			>
				{{ summary.agent_name }}
			</div>
			<div v-if="summary.rule" class="rule">
				{{ summary.rule }}
			</div>
		</div>
		<div class="flex min-w-12.5 items-center justify-center bg-default font-mono font-bold">
			<span v-if="summary.number_of_alerts">
				{{ summary.number_of_alerts }}
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AlertsByHost, AlertsByRule, AlertsByRulePerHost } from "@/types/alerts"

const { summary } = defineProps<{ summary: Partial<AlertsByHost & AlertsByRule & AlertsByRulePerHost> }>()
</script>
