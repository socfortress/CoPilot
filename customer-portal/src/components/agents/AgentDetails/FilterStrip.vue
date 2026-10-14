<template>
	<!-- Counts that are also the filter: one cell per option, the selected one underlined. -->
	<div
		class="border-default bg-default grid overflow-hidden rounded-lg border"
		:style="{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }"
		role="group"
		:aria-label="label"
	>
		<button
			v-for="(option, index) of options"
			:key="option.value"
			type="button"
			class="hover:bg-secondary/60 focus-visible:outline-primary flex min-w-0 cursor-pointer flex-col gap-1.5 px-2 py-2.5 text-left transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 @md:px-3"
			:class="[
				{ 'border-default border-l': index > 0 },
				model === option.value ? 'bg-secondary shadow-[inset_0_-2px_0_var(--primary-color)]' : ''
			]"
			:aria-pressed="model === option.value"
			:data-testid="`${testid}-${option.testid ?? option.value}`"
			@click="model = option.value"
		>
			<!-- The label alone on its line, so "Critical" fits a fifth of a phone; the dot rides with the count. -->
			<span class="text-tertiary text-xxs truncate font-medium tracking-wider uppercase @md:tracking-[0.12em]">
				{{ option.label }}
			</span>
			<span class="flex min-w-0 items-center gap-1.5">
				<span class="size-1.5 shrink-0 rounded-full" :class="option.dot" aria-hidden="true" />
				<span
					class="font-mono text-lg leading-none font-semibold tabular-nums"
					:class="loading ? 'text-tertiary' : 'text-default'"
					:data-testid="`${testid}-count`"
				>
					{{ loading ? "—" : option.count.toLocaleString() }}
				</span>
			</span>
		</button>
	</div>
</template>

<script setup lang="ts" generic="T extends string">
/**
 * The header strip of an agent's findings (#1256): how many of each kind, each cell also
 * the filter for that kind. Shared by the Vulnerabilities and SCA tabs so both read alike.
 */

export interface FilterStripOption<V extends string = string> {
	value: V
	label: string
	count: number
	/** Tailwind background class of the dot: the kind's colour. */
	dot: string
	/** The `data-testid` suffix, when the value is not one (it has spaces). */
	testid?: string
}

const {
	options,
	label,
	testid,
	loading = false
} = defineProps<{
	options: FilterStripOption<T>[]
	label: string
	/** Prefix of every cell's `data-testid`: `<testid>-<value>`, and `<testid>-count`. */
	testid: string
	loading?: boolean
}>()

const model = defineModel<T>({ required: true })
</script>
