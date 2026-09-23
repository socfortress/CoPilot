<template>
	<div class="status-legend" :class="`status-legend--${variant}`" role="list">
		<div v-for="segment of segments" :key="segment.key" class="status-legend__item" role="listitem">
			<template v-if="variant === 'inline'">
				<StatusDot :color="segment.color" />
				<span class="status-legend__value">{{ segment.value }}</span>
				<span>{{ segment.label }}</span>
			</template>

			<template v-else>
				<span class="flex items-center gap-1.5">
					<StatusDot :color="segment.color" />
					{{ segment.label }}
				</span>
				<span class="status-legend__leader" aria-hidden="true" />
				<span class="status-legend__value">{{ segment.value }}</span>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { StatusSegment } from "./status"
import StatusDot from "./StatusDot.vue"

const { variant = "inline" } = defineProps<{
	segments: StatusSegment[]
	/**
	 * `inline` — a wrapping row of "● 9 open", for a compact breakdown under a number.
	 * `stacked` — one segment per line, label and value joined by a leader line.
	 */
	variant?: "inline" | "stacked"
}>()
</script>

<style lang="scss" scoped>
.status-legend {
	display: flex;
	font-size: 12px;
	line-height: 16px;
	color: var(--fg-secondary-color);

	&__item {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	&__value {
		font-family: var(--font-family-mono);
		font-variant-numeric: tabular-nums;
		color: var(--fg-default-color);
	}

	&--inline {
		flex-wrap: wrap;
		align-items: center;
		gap: 4px 12px;
	}

	&--stacked {
		flex-direction: column;
		gap: 6px;

		.status-legend__item {
			gap: 12px;
		}
	}

	&__leader {
		flex-grow: 1;
		height: 1px;
		background-color: var(--border-color);
	}
}
</style>
