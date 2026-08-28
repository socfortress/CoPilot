<template>
	<div class="flex items-center gap-2.5">
		<span class="w-2/5 max-w-65 shrink-0 truncate font-mono text-[11.5px]" :title="label">{{ label }}</span>
		<div class="h-1.5 grow overflow-hidden rounded-full bg-[rgba(var(--fg-secondary-color-rgb)/0.16)]">
			<div
				class="h-full rounded-full transition-[width] duration-300"
				:class="accent === 'warning' ? 'bg-warning' : 'bg-primary'"
				:style="{ width: pct(value, max) }"
			/>
		</div>
		<span
			class="text-secondary text-2xs [&_b]:text-default shrink-0 text-end font-mono [&_b]:font-semibold"
			:class="wide ? 'w-24' : 'w-12'"
		>
			<slot>{{ fmt(value) }}</slot>
		</span>
	</div>
</template>

<script setup lang="ts">
import { fmt, pct } from "./format"

/**
 * Label + proportional bar + trailing figure. Shared by the threshold panel's top
 * offenders and the top-values cards, which were two near-identical markup blocks.
 */
withDefaults(
	defineProps<{
		label: string
		/** Drives the bar width. */
		value: number
		/** Largest value in this group — the bar is relative to it. */
		max: number
		accent?: "primary" | "warning"
		/** Wider trailing column, for rows whose figure is more than a number. */
		wide?: boolean
	}>(),
	{ accent: "primary", wide: false }
)
</script>
