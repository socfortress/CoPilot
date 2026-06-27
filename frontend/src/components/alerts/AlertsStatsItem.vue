<template>
	<div class="border-default bg-secondary flex items-stretch overflow-hidden rounded-lg border">
		<div class="border-default flex grow flex-col justify-center gap-1 border-r px-5 py-4">
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
		<div class="bg-default flex min-w-12.5 items-center justify-center font-mono font-bold">
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
