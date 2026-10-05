<template>
	<!-- The total (with how it splits) first, then one cell per figure: one strip, split by hairlines. -->
	<section
		class="bg-default border-default divide-border grid grid-cols-2 divide-y overflow-hidden rounded-lg border @3xl:divide-x @3xl:divide-y-0"
		:class="WIDE_COLUMNS[cells.length + 1]"
		:aria-label="`${entity} by status`"
		data-testid="status-strip"
	>
		<div class="col-span-2 flex min-w-0 flex-col gap-2.5 px-4 py-3 @3xl:col-span-1" data-testid="stat-total">
			<span class="text-tertiary flex items-center gap-1.5 text-xs">
				<Icon :name="icon" :size="14" />
				Total {{ entity.toLowerCase() }}
			</span>
			<span
				class="font-display text-2xl leading-none font-semibold tabular-nums"
				data-testid="stat-value"
				v-text="formatCount(total)"
			/>
			<StatusBar :segments="split ?? cells" />
		</div>

		<div
			v-for="(cell, index) of cells"
			:key="cell.key"
			class="border-border flex min-w-0 flex-col gap-2.5 px-4 py-3 @max-3xl:odd:border-l"
			:class="{
				'is-lifted': lifted(cell),
				// Two to a row when narrow: an odd last cell takes the whole row, not half of it.
				'col-span-2 @3xl:col-span-1': cells.length % 2 === 1 && index === cells.length - 1
			}"
			:data-testid="`stat-${cell.key}`"
		>
			<span class="text-tertiary flex min-w-0 items-center gap-1.5 text-xs whitespace-nowrap">
				<!-- A dot is a share of the bar; an icon marks a flag counted across it. -->
				<Icon v-if="cell.icon" :name="cell.icon" :size="12" :class="textClass(cell.color)" />
				<span v-else class="size-2 shrink-0 rounded-full" :class="bgClass(cell.color)" aria-hidden="true" />
				<span class="truncate first-letter:uppercase">{{ cell.label }}</span>
			</span>
			<div class="flex items-baseline justify-between gap-2">
				<span
					class="font-display text-2xl leading-none font-semibold tabular-nums"
					:class="{ 'text-primary': lifted(cell) }"
					data-testid="stat-value"
					v-text="formatCount(cell.value)"
				/>
				<span
					class="text-tertiary font-mono text-xs tabular-nums"
					data-testid="stat-share"
					v-text="share(cell.value)"
				/>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
// The counts above a list (alerts, cases, agents), in the Overview's voice: the total
// with its split as the Overview's bar, then each figure with its share of the total.
// Colours are the shared status palette (overview/shared/status.ts), so a colour means
// the same thing here, in the lists and on the Overview. `split` is what the bar shows
// when it is not simply the cells — a flag such as "critical" is a cell (marked with an
// icon) but no share of the bar. `lift` names the one cell to raise while it is not zero:
// the figure the customer acts on.
import type { StatusSegment } from "@/components/overview/shared/status"
import Icon from "@/components/common/Icon.vue"
import { bgClass, textClass } from "@/components/overview/shared/status"
import StatusBar from "@/components/overview/shared/StatusBar.vue"

export interface StatusStripCell extends StatusSegment {
	/** Marks a flag counted across the split (no dot, and not in the bar). */
	icon?: string
}

const { total, entity, icon, cells, split, lift } = defineProps<{
	total: number
	/** "Alerts", "Cases", "Agents": names the strip and its total. */
	entity: string
	icon: string
	cells: StatusStripCell[]
	/** What the bar under the total shows; the cells when left out. */
	split?: StatusSegment[]
	/** The key of the cell to raise while it is not zero. */
	lift?: string
}>()

// Full class names, so Tailwind finds them: the total plus 3 or 4 cells.
const WIDE_COLUMNS: Record<number, string> = { 4: "@3xl:grid-cols-4", 5: "@3xl:grid-cols-5" }

function lifted(cell: StatusStripCell) {
	return cell.key === lift && cell.value > 0
}

function formatCount(value: number) {
	return value.toLocaleString("en-US")
}

/** The share of the total, as a whole percent; nothing when there is no total. */
function share(value: number) {
	return total ? `${Math.round((value / total) * 100)}%` : ""
}
</script>

<style scoped>
.is-lifted {
	background-color: rgb(var(--primary-color-rgb) / 0.06);
}
</style>
