<template>
	<!-- Counts that are also the filter: one cell per option, the selected one underlined. -->
	<!-- Five or more cells don't fit a narrow column side by side: there the first ("All") takes a
	     row of its own and the rest share the next one. -->
	<div
		class="border-default bg-default grid overflow-hidden rounded-lg border"
		:class="
			split
				? 'grid-cols-[repeat(var(--rest),minmax(0,1fr))] @lg:grid-cols-[repeat(var(--all),minmax(0,1fr))]'
				: 'grid-cols-[repeat(var(--all),minmax(0,1fr))]'
		"
		:style="{ '--all': options.length, '--rest': options.length - 1 }"
		role="group"
		:aria-label="label"
		:data-split="split || undefined"
	>
		<button
			v-for="(option, index) of options"
			:key="option.value"
			type="button"
			class="hover:bg-secondary/60 focus-visible:outline-primary flex min-w-0 cursor-pointer flex-col gap-1.5 px-2 py-2.5 text-left transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 @md:px-3"
			:class="[
				cellLayout(index),
				model === option.value ? 'bg-secondary shadow-[inset_0_-2px_0_var(--primary-color)]' : ''
			]"
			:aria-pressed="model === option.value"
			:data-testid="`${testid}-${option.testid ?? option.value}`"
			@click="model = option.value"
		>
			<!-- The label alone on its line, so "Critical" fits a fifth of a phone; the dot rides with the count. -->
			<span
				class="text-tertiary text-xxs min-w-0 truncate font-medium tracking-wider uppercase @md:tracking-[0.12em]"
			>
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
import { computed } from "vue"

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

const split = computed(() => options.length > 4)

/** The cell's borders and, when split, the first cell's own row: label and count side by side. */
function cellLayout(index: number): string[] {
	if (!split.value) return index > 0 ? ["border-default border-l"] : []
	if (index === 0) {
		return [
			"col-span-full @lg:col-span-1 border-default border-b @lg:border-b-0",
			"flex-row! items-center justify-between @lg:flex-col! @lg:items-start @lg:justify-start"
		]
	}
	return index === 1 ? ["border-default @lg:border-l"] : ["border-default border-l"]
}
</script>
