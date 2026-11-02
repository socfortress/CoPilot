<template>
	<span v-if="state?.kind === 'switch'" class="section-mark" :title="state.word">
		<span class="section-led" :class="{ 'is-on': state.on }" aria-hidden="true"></span>
		<span v-if="withWord" class="section-word">{{ state.word }}</span>
		<span v-else class="sr-only">{{ state.word }}</span>
	</span>
	<span v-else-if="state?.kind === 'count'" class="section-mark" :title="state.word">
		<span v-if="withWord" class="section-word">{{ state.word }}</span>
		<template v-else>
			<span class="section-count" aria-hidden="true">{{ state.count }}</span>
			<span class="sr-only">{{ state.word }}</span>
		</template>
	</span>
</template>

<script setup lang="ts">
import type { SectionState } from "./sections"

/**
 * A section's state beside its name: a light for a switch (filled when on, a ring when off, so it
 * never relies on colour alone), a count for a list. `withWord` writes the state out ("On",
 * "English only", "3 sources") instead of the count.
 */
const { state, withWord = false } = defineProps<{
	state: SectionState | null
	withWord?: boolean
}>()
</script>

<style lang="scss" scoped>
.section-mark {
	display: inline-flex;
	align-items: center;
	gap: 7px;
	flex-shrink: 0;
}

.section-led {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	box-sizing: border-box;
	border: 1.5px solid var(--fg-secondary-color);

	&.is-on {
		border: 0;
		background-color: var(--success-color);
		box-shadow: 0 0 0 3px rgba(var(--success-color-rgb), 0.16);
	}
}

.section-word {
	font-size: 12px;
	color: var(--fg-secondary-color);
	white-space: nowrap;
	text-transform: uppercase;
	line-height: 0;
}

.section-count {
	min-width: 20px;
	padding: 0 6px;
	box-sizing: border-box;
	border: 1px solid var(--border-color);
	border-radius: 9px;
	font-family: var(--font-family-mono);
	font-size: 11px;
	line-height: 16px;
	text-align: center;
	color: var(--fg-secondary-color);
}
</style>
