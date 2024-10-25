<template>
	<div class="alerts-stats-item flex items-stretch">
		<div class="info flex grow flex-col justify-center gap-1">
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
		<div class="count flex items-center justify-center font-mono">
			<span v-if="summary.number_of_alerts">
				{{ summary.number_of_alerts }}
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AlertsByHost, AlertsByRule, AlertsByRulePerHost } from "@/types/alerts.d"

const { summary } = defineProps<{ summary: Partial<AlertsByHost & AlertsByRule & AlertsByRulePerHost> }>()
</script>

<style lang="scss" scoped>
.alerts-stats-item {
	border-radius: var(--border-radius);
	overflow: hidden;
	background-color: var(--bg-secondary-color);
	border: var(--border-small-100);

	.info {
		border-right: var(--border-small-100);
		padding: 16px 20px;
	}

	.count {
		min-width: 50px;
		background-color: var(--bg-color);
		font-weight: bold;
	}
}
</style>
