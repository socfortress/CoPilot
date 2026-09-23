<template>
	<div
		class="grid-cols-activity-row @max-md/activity-list:grid-cols-activity-row-stacked grid gap-x-3.5 py-3 pr-5 pl-4 @max-md/activity-list:gap-y-2.5"
		:class="{ 'hover:bg-hover focus-within:bg-hover transition-colors motion-reduce:transition-none': interactive }"
		role="listitem"
	>
		<!-- A thin status rail: the colour reads at a glance without a chip competing with the title. -->
		<span
			class="w-0.75 self-stretch rounded-full opacity-85 @max-md/activity-list:row-span-2"
			:class="railClass"
			aria-hidden="true"
		/>

		<div class="flex min-w-0 flex-col gap-1">
			<slot />
		</div>

		<!-- Narrow lists: time and actions drop under the text instead of squeezing it. -->
		<div
			class="flex flex-col items-end justify-between gap-2 @max-md/activity-list:col-start-2 @max-md/activity-list:flex-row @max-md/activity-list:items-center"
		>
			<slot name="aside" />
		</div>
	</div>
</template>

<script setup lang="ts">
/**
 * The row grid shared by real items and their skeletons: a status rail, the text
 * column and a right-hand column (time on top, actions at the bottom). Both render
 * through this component, so a placeholder cannot drift from the row it stands for.
 * Responsive rules read the width of the enclosing ActivityList (`@container/activity-list`).
 */
const { interactive = true } = defineProps<{
	/** Background utility for the rail, e.g. `bg-info`. */
	railClass: string
	/** Hover and focus highlight; off for placeholders. */
	interactive?: boolean
}>()
</script>
