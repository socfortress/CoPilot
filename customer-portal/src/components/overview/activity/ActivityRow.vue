<template>
	<div class="activity-row" :class="{ 'activity-row--interactive': interactive }" role="listitem">
		<span class="activity-row__rail" :style="{ backgroundColor: railColor }" aria-hidden="true" />

		<div class="activity-row__content">
			<slot />
		</div>

		<div class="activity-row__aside">
			<slot name="aside" />
		</div>
	</div>
</template>

<script setup lang="ts">
/**
 * The row grid shared by real items and their skeletons: a status rail, the text
 * column and a right-hand column (time on top, actions at the bottom). Both render
 * through this component, so a placeholder cannot drift from the row it stands for.
 */
const { interactive = true } = defineProps<{
	railColor: string
	/** Hover and focus highlight; off for placeholders. */
	interactive?: boolean
}>()
</script>

<style lang="scss" scoped>
.activity-row {
	display: grid;
	grid-template-columns: 3px minmax(0, 1fr) auto;
	column-gap: 14px;
	padding: 12px 20px 12px 17px;

	& + & {
		border-top: 1px solid var(--border-color);
	}

	&--interactive {
		transition: background-color 0.2s ease;

		&:hover,
		&:focus-within {
			background-color: var(--hover-color);
		}
	}

	// A thin rail on the leading edge: the status colour reads at a glance without
	// a chip competing with the title.
	&__rail {
		width: 3px;
		border-radius: 3px;
		align-self: stretch;
		opacity: 0.85;
	}

	&__content {
		display: flex;
		min-width: 0;
		flex-direction: column;
		gap: 4px;
	}

	&__aside {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		justify-content: space-between;
		gap: 8px;
	}

	// Narrow panels: time and actions drop under the text instead of squeezing it.
	@container activity-list (max-width: 440px) {
		grid-template-columns: 3px minmax(0, 1fr);
		row-gap: 10px;

		&__rail {
			grid-row: span 2;
		}

		&__aside {
			grid-column: 2;
			flex-direction: row;
			align-items: center;
		}
	}
}

@media (prefers-reduced-motion: reduce) {
	.activity-row--interactive {
		transition: none;
	}
}
</style>
