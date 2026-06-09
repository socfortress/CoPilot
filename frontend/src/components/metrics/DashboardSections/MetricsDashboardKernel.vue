<template>
	<section class="@container flex flex-col gap-4">
		<h3 class="text-lg font-semibold">Kernel</h3>

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

		<div class="grid grid-cols-1 gap-4 @lg:grid-cols-2">
			<CardEntity v-for="chart in kernelCharts" :key="chart.id" size="small" main-box-class="gap-0">
				<template #headerMain>
					<span class="text-secondary text-xs font-medium uppercase">{{ chart.title }}</span>
				</template>
				<template #default>
					<ChartArea
						:labels="chart.labels"
						:data="chart.data"
						:series-names="chart.seriesNames"
						labels-datetime
						y-axis-name="/s"
						:height="220"
					/>
				</template>
			</CardEntity>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { MetricsKernelData, TimeSeriesData } from "@/types/metrics.d"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"

const { kernel } = defineProps<{
	kernel: MetricsKernelData
}>()

interface KernelStatTile {
	id: string
	title: string
	value: string
	color?: CardLinkColor
}

interface KernelChartConfig {
	id: string
	title: string
	labels: string[]
	data: number[] | number[][]
	seriesNames: string[]
}

const kernelMetrics = [
	{ id: "interrupts", title: "Interrupts/sec", shortTitle: "Interrupts" },
	{ id: "processes-forked", title: "Processes Forked/sec", shortTitle: "Processes Forked" }
] as const

type KernelMetricId = (typeof kernelMetrics)[number]["id"]

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

function latestSeriesValue(data: TimeSeriesData | undefined): number | null {
	const firstSeries = Object.values(data ?? {})[0]
	const lastPoint = firstSeries?.at(-1)
	return lastPoint?.value ?? null
}

function formatMetricRate(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}/s`
}

const metricSeriesById = computed((): Record<KernelMetricId, TimeSeriesData | undefined> => ({
	interrupts: kernel.interrupts,
	"processes-forked": kernel.processes_forked
}))

const statTiles = computed<KernelStatTile[]>(() =>
	kernelMetrics.map(metric => ({
		id: metric.id,
		title: metric.shortTitle,
		value: formatMetricRate(latestSeriesValue(metricSeriesById.value[metric.id])),
		color: metric.id === "interrupts" ? "primary" : undefined
	}))
)

const kernelCharts = computed<KernelChartConfig[]>(() =>
	kernelMetrics.map(metric => {
		const series = metricSeriesById.value[metric.id]
		const transformed = transformSeries(series)

		return {
			id: metric.id,
			title: metric.title,
			...transformed
		}
	})
)
</script>
