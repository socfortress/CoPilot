<template>
	<svg
		:viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
		preserveAspectRatio="none"
		class="block overflow-visible"
		role="img"
		:aria-label="label"
	>
		<title>{{ label }}</title>
		<polyline
			v-if="points"
			:points
			fill="none"
			:stroke="color"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			vector-effect="non-scaling-stroke"
		/>
		<line
			v-else
			x1="0"
			:y1="HEIGHT - 1"
			:x2="WIDTH"
			:y2="HEIGHT - 1"
			:stroke="color"
			stroke-width="2"
			stroke-dasharray="2 4"
			vector-effect="non-scaling-stroke"
		/>
	</svg>
</template>

<script setup lang="ts">
import { computed } from "vue"

const { values, color = "currentColor" } = defineProps<{
	values: number[]
	/** What the line shows, for screen readers and as the hover title. */
	label: string
	color?: string
}>()

const WIDTH = 100
const HEIGHT = 28

/** `null` when there is nothing to draw: a flat dashed baseline says "nothing", not "zero growth". */
const points = computed(() => {
	const max = Math.max(...values, 0)
	if (values.length < 2 || max === 0) return null
	const step = WIDTH / (values.length - 1)
	// 1 unit of headroom top and bottom, so a 2px line is never clipped.
	return values
		.map((value, i) => `${(i * step).toFixed(2)},${(HEIGHT - 1 - (value / max) * (HEIGHT - 2)).toFixed(2)}`)
		.join(" ")
})
</script>
