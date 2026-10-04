<template>
	<n-tooltip :disabled="stats.median == null" placement="top">
		<template #trigger>
			<div
				class="duration-cell flex cursor-help flex-col items-end gap-0.5 font-mono tabular-nums"
				data-testid="duration-cell"
			>
				<span
					class="text-sm leading-tight"
					:class="stats.median == null ? 'text-tertiary' : 'text-default font-medium'"
				>
					{{ formatDuration(stats.median) }}
				</span>
				<span v-if="stats.median != null" class="text-2xs inline-flex items-baseline gap-1 leading-tight">
					<span class="text-tertiary tracking-wider uppercase">p90</span>
					<span class="text-secondary">{{ formatDuration(stats.p90) }}</span>
				</span>
			</div>
		</template>
		<dl
			class="m-0 grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5 font-mono text-xs"
			data-testid="duration-cell-tooltip"
		>
			<dt class="text-secondary">median</dt>
			<dd class="m-0 text-right">{{ formatDuration(stats.median) }}</dd>
			<dt class="text-secondary">mean</dt>
			<dd class="m-0 text-right">{{ formatDuration(stats.mean) }}</dd>
			<dt class="text-secondary">p90</dt>
			<dd class="m-0 text-right">{{ formatDuration(stats.p90) }}</dd>
			<dt class="text-secondary">items</dt>
			<dd class="m-0 text-right">{{ formatCount(stats.count) }}</dd>
		</dl>
	</n-tooltip>
</template>

<script setup lang="ts">
// A duration statistic in a table cell — time to acknowledge, time to resolve — read the
// same way in every column that shows one: the median first and largest (one bulk close
// of old noise cannot move it), the 90th percentile under it for the tail, right-aligned
// like every figure. The mean and the sample size are a hover away. No outcome yet reads
// as a dash, never as 0.
import type { DurationStats } from "@/types/soc-management"
import { NTooltip } from "naive-ui"
import { formatCount, formatDuration } from "../utils"

const { stats } = defineProps<{ stats: DurationStats }>()
</script>
