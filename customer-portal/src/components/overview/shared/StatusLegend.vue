<template>
	<div
		class="text-secondary flex text-xs leading-4"
		:class="variant === 'inline' ? 'flex-wrap items-center gap-x-3 gap-y-1' : 'flex-col gap-1.5'"
		role="list"
	>
		<div
			v-for="segment of segments"
			:key="segment.key"
			class="flex items-center"
			:class="variant === 'inline' ? 'gap-1.5' : 'gap-3'"
			role="listitem"
		>
			<template v-if="variant === 'inline'">
				<StatusDot :color="segment.color" />
				<span class="text-default font-mono tabular-nums">{{ segment.value }}</span>
				<span>{{ segment.label }}</span>
			</template>

			<template v-else>
				<span class="flex items-center gap-1.5">
					<StatusDot :color="segment.color" />
					{{ segment.label }}
				</span>
				<span class="bg-border h-px grow" aria-hidden="true" />
				<span class="text-default font-mono tabular-nums">{{ segment.value }}</span>
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
