<template>
	<section
		class="border-default bg-default flex flex-col overflow-hidden rounded-lg border"
		data-testid="waf-rank-list"
	>
		<header class="bg-secondary border-default flex items-baseline justify-between gap-2 border-b px-4 py-2">
			<span :class="SECTION_LABEL">{{ title }}</span>
			<span v-if="caption" class="text-tertiary text-2xs font-mono">{{ caption }}</span>
		</header>
		<n-empty v-if="!items.length" :description="emptyText" class="min-h-32 justify-center" size="small" />
		<!-- One grid per row: rank, the label over its meter, then the figure and its share. -->
		<div v-else class="divide-border flex flex-col divide-y">
			<div
				v-for="(item, index) of items"
				:key="item.key"
				class="group hover:bg-secondary/50 grid grid-cols-[1.75rem_minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-2 transition-colors"
				data-testid="waf-rank-row"
			>
				<span class="text-tertiary font-mono text-xs tabular-nums">
					{{ String(index + 1).padStart(2, "0") }}
				</span>

				<span class="flex min-w-0 flex-col gap-1.5">
					<span class="flex min-w-0 items-center gap-2 text-sm">
						<slot name="label" :item>
							<span class="text-default truncate" :class="{ 'font-mono text-xs': mono }">
								{{ item.label }}
							</span>
						</slot>
					</span>
					<!-- The meter: one hue, the track a lighter step of it, so magnitude reads across the list. -->
					<span class="block h-1 w-full overflow-hidden rounded-full" :style="{ background: trackColor }">
						<span
							class="block h-full rounded-full transition-[width] duration-500"
							:style="{ width: `${Math.max(2, (item.value / max) * 100)}%`, background: markColor }"
						/>
					</span>
				</span>

				<span class="flex items-center gap-2">
					<slot name="actions" :item />
					<span class="flex min-w-14 flex-col items-end leading-tight">
						<span class="text-default font-mono text-sm tabular-nums">{{ formatCount(item.value) }}</span>
						<span class="text-tertiary text-2xs font-mono tabular-nums">{{ share(item.value) }}</span>
					</span>
				</span>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useWafChartColors } from "./chart-colors"

export interface WafRankItem {
	key: string
	label: string
	value: number
	[extra: string]: unknown
}

const {
	title,
	items,
	caption,
	mono = false,
	emptyText = "Nothing in this window"
} = defineProps<{
	title: string
	items: WafRankItem[]
	caption?: string
	mono?: boolean
	emptyText?: string
}>()

const { markColor, trackColor } = useWafChartColors()
const max = computed(() => Math.max(1, ...items.map(i => i.value)))
const total = computed(() => items.reduce((sum, i) => sum + i.value, 0))
const formatCount = (n: number) => n.toLocaleString()

/** The item's share of what the list shows (not of all traffic): the lists are top-N. */
function share(value: number) {
	if (!total.value) return ""
	const pct = (value / total.value) * 100
	return `${pct < 1 && pct > 0 ? "<1" : Math.round(pct)}%`
}
</script>
