<template>
	<section class="@container flex flex-col gap-4">
		<h3 class="text-lg font-semibold">Memory</h3>

		<div class="grid grid-cols-1 gap-3 @md:grid-cols-2">
			<CardLink
				v-for="tile in statTiles"
				:key="tile.id"
				size="small"
				:title="tile.title"
				:value="tile.value"
				:color="tile.color"
			/>
		</div>

		<CardEntity size="small" main-box-class="gap-0">
			<template #headerMain>
				<span class="text-secondary text-xs font-medium uppercase">Memory Usage</span>
			</template>
			<template #default>
				<ChartArea
					:labels="memUsedChart.labels"
					:data="memUsedChart.data"
					:series-names="memUsedChart.seriesNames"
					labels-datetime
					use-format-bytes
					:height="220"
				/>
			</template>
		</CardEntity>
	</section>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { MetricsMemoryData, TimeSeriesData } from "@/types/metrics.d"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"
import { formatBytes } from "@/utils/format"

const { memory } = defineProps<{
	memory: MetricsMemoryData
}>()

interface MemoryStatTile {
	id: string
	title: string
	value: string
	color?: CardLinkColor
}

function transformSeries(data: TimeSeriesData | undefined) {
	const series = data ?? {}
	const labels = Object.values(series)[0]?.map(point => point.time) ?? []
	const rows = Object.values(series).map(points => points.map(point => point.value))

	return {
		labels,
		data: rows.length <= 1 ? (rows[0] ?? []) : rows,
		seriesNames: Object.keys(series)
	}
}

function formatMetricBytes(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return formatBytes(value) ?? "—"
}

function swapFreeColor(swapFree: number | null | undefined, swapTotal: number | null | undefined): CardLinkColor | undefined {
	if (swapFree === null || swapFree === undefined || swapTotal === null || swapTotal === undefined || swapTotal <= 0) {
		return undefined
	}

	const ratio = swapFree / swapTotal
	if (ratio < 0.2) return "danger"
	if (ratio < 0.5) return "warning"
	return "success"
}

const statTiles = computed<MemoryStatTile[]>(() => [
	{
		id: "swap-total",
		title: "Swap Total",
		value: formatMetricBytes(memory.swap_total),
		color: "primary"
	},
	{
		id: "swap-free",
		title: "Swap Free",
		value: formatMetricBytes(memory.swap_free),
		color: swapFreeColor(memory.swap_free, memory.swap_total)
	}
])

const memUsedChart = computed(() => transformSeries(memory.mem_used))
</script>
