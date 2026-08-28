<template>
	<component :is="tag" class="text-default text-3xs flex items-center gap-2 font-bold tracking-widest uppercase">
		<span class="h-2.75 w-0.5 shrink-0 rounded-xs" :class="accent === 'warning' ? 'bg-warning' : 'bg-border'" />
		<slot />
		<span class="bg-border h-px grow" />
	</component>
</template>

<script setup lang="ts">
/**
 * Heading for a block of findings or values.
 *
 * The accent tick and the fading rule are what make it read as a heading: plain
 * muted uppercase sat at the same visual weight as the small mono labels right
 * underneath it, so it looked like just another row of data.
 */
withDefaults(
	defineProps<{
		/** Heading level — these blocks nest, so the caller picks the right one. */
		tag?: string
		/** Tick colour; `warning` is for headings inside the threshold panel. */
		accent?: "primary" | "warning"
	}>(),
	{ tag: "h4", accent: "primary" }
)
</script>
