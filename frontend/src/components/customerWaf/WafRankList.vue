<template>
	<section class="border-default flex flex-col overflow-hidden rounded-lg border">
		<header class="bg-secondary border-default flex items-baseline justify-between gap-2 border-b px-3 py-2">
			<span :class="SECTION_LABEL">{{ title }}</span>
			<span v-if="caption" class="text-tertiary text-2xs">{{ caption }}</span>
		</header>
		<n-empty v-if="!items.length" :description="emptyText" class="min-h-32 justify-center" size="small" />
		<ol v-else class="flex flex-col gap-2.5 p-3">
			<li v-for="item of items" :key="item.key" class="group flex flex-col gap-1">
				<div class="flex items-center justify-between gap-3 text-sm">
					<span class="flex min-w-0 items-center gap-2">
						<slot name="label" :item>
							<span class="truncate" :class="{ 'font-mono text-xs': mono }">{{ item.label }}</span>
						</slot>
					</span>
					<span class="flex shrink-0 items-center gap-2">
						<slot name="actions" :item />
						<span class="text-default font-mono text-xs tabular-nums">{{ formatCount(item.value) }}</span>
					</span>
				</div>
				<!-- The meter: one hue, the track a lighter step of it, so magnitude reads across the whole row. -->
				<div class="h-1.5 w-full overflow-hidden rounded-full" :style="{ background: trackColor }">
					<div
						class="h-full rounded-full transition-[width] duration-500"
						:style="{ width: `${Math.max(2, (item.value / max) * 100)}%`, background: markColor }"
					/>
				</div>
			</li>
		</ol>
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
const formatCount = (n: number) => n.toLocaleString()
</script>
