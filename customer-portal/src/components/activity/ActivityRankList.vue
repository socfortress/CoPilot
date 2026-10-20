<template>
	<ol class="flex flex-col gap-3 px-5 py-4" :data-testid="testid">
		<li
			v-for="item of items"
			:key="item.key"
			class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)_auto]"
			:data-testid="`${testid}-row`"
			:data-key="item.key"
		>
			<component
				:is="linkFor(item, 'current') ? RouterLink : 'span'"
				:to="linkFor(item, 'current') ?? undefined"
				class="text-default min-w-0 truncate text-sm no-underline"
				:class="{
					'hover:text-primary focus-visible:text-primary focus-visible:outline-primary rounded transition-colors focus-visible:outline-2 focus-visible:outline-offset-2':
						!!linkFor(item, 'current')
				}"
				:title="label(item)"
				data-testid="activity-row-label"
			>
				<bdi>{{ label(item) }}</bdi>
			</component>

			<!-- This period as the bar, the period before as a tick on the same scale. -->
			<div
				class="bg-body relative order-last col-span-2 h-2 rounded-full sm:order-none sm:col-span-1"
				role="presentation"
			>
				<div
					class="absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ease-out motion-reduce:transition-none"
					:style="{ width: `${barWidth(item.count, scale)}%`, backgroundColor: colors.current }"
				/>
				<div
					v-if="item.previous > 0"
					class="absolute -inset-y-1 w-0.5 rounded-full"
					:style="{
						left: `calc(${barWidth(item.previous, scale)}% - 1px)`,
						backgroundColor: colors.previous
					}"
					:title="`The period before: ${item.previous}`"
				/>
			</div>

			<!-- Fixed widths, so every row's bar ends at the same place. -->
			<div
				class="grid grid-cols-[2.5rem_3.5rem] items-baseline gap-x-1 font-mono text-xs whitespace-nowrap tabular-nums md:grid-cols-[2.5rem_3.5rem_4rem]"
			>
				<component
					:is="linkFor(item, 'current') ? RouterLink : 'span'"
					:to="linkFor(item, 'current') ?? undefined"
					class="text-default hover:text-primary text-right text-sm font-semibold no-underline transition-colors"
					:aria-label="`${item.count} this period`"
					data-testid="activity-row-count"
				>
					{{ item.count }}
				</component>
				<span
					class="text-secondary flex items-center pl-1"
					title="Change from the period before"
					data-testid="activity-row-delta"
				>
					<Icon v-if="delta(item).direction === 'up'" name="carbon:arrow-up" :size="12" />
					<Icon v-else-if="delta(item).direction === 'down'" name="carbon:arrow-down" :size="12" />
					{{ delta(item).text }}
				</span>
				<component
					:is="linkFor(item, 'previous') && item.previous ? RouterLink : 'span'"
					:to="(item.previous && linkFor(item, 'previous')) || undefined"
					class="text-tertiary hover:text-primary hidden text-right no-underline transition-colors md:inline"
					:aria-label="`${item.previous} the period before`"
					data-testid="activity-row-previous"
				>
					was {{ item.previous }}
				</component>
			</div>
		</li>
	</ol>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router"
import type { Period } from "./activity"
import type { ActivityCount } from "@/types/activity"
import { computed } from "vue"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { TREND_COLORS } from "@/components/overview/trend/trend"
import { useThemeStore } from "@/stores/theme"
import { barWidth, countDelta, panelMax, sliceLabel } from "./activity"

/**
 * A breakdown as a ranked list of bars (#1284): this period's count as the bar, in the
 * hue the Overview's trend gives alerts opened, and the period before as a neutral tick on
 * the same scale. The numbers are always written out, and a row whose slice can be listed
 * links to exactly the alerts it counted.
 */

const {
	items,
	link,
	labelKind = null,
	testid
} = defineProps<{
	items: ActivityCount[]
	/** Where a row's count leads, per period; none when the slice cannot be listed. */
	link?: (item: ActivityCount, period: Period) => RouteLocationRaw | null
	labelKind?: "status" | null
	testid: string
}>()

const themeStore = useThemeStore()
const colors = computed(() => {
	const palette = TREND_COLORS[themeStore.isThemeDark ? "dark" : "light"]
	return { current: palette.opened, previous: palette.open }
})

const scale = computed(() => panelMax(items))

function linkFor(item: ActivityCount, period: Period): RouteLocationRaw | null {
	return link ? link(item, period) : null
}

function label(item: ActivityCount): string {
	return sliceLabel(item, labelKind)
}

function delta(item: ActivityCount) {
	return countDelta(item.count, item.previous)
}
</script>
