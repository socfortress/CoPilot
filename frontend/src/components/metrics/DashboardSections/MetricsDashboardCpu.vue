<template>
	<section class="@container flex flex-col gap-4">
		<h3 class="text-lg font-semibold">CPU</h3>

		<div class="grid grid-cols-1 gap-3 @md:grid-cols-2 @3xl:grid-cols-4">
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
			<CardEntity v-for="chart in cpuCharts" :key="chart.id" size="small" main-box-class="gap-0">
				<template #headerMain>
					<span class="text-secondary text-xs font-medium uppercase">{{ chart.title }}</span>
				</template>
				<template #default>
					<ChartArea
						:labels="chart.labels"
						:data="chart.data"
						:series-names="chart.seriesNames"
						labels-datetime
						y-axis-name="%"
						:height="220"
					/>
				</template>
			</CardEntity>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { MetricsCpuData, TimeSeriesData } from "@/types/metrics.d"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"

const { cpu } = defineProps<{
	cpu: MetricsCpuData
}>()

interface CpuStatTile {
	id: string
	title: string
	value: string
	color?: CardLinkColor
}

interface CpuChartConfig {
	id: string
	title: string
	labels: string[]
	data: number[] | number[][]
	seriesNames: string[]
}

const cpuMetrics = [
	{ id: "system", title: "CPU System %", shortTitle: "System" },
	{ id: "user", title: "CPU User %", shortTitle: "User" },
	{ id: "iowait", title: "I/O Wait %", shortTitle: "I/O Wait" },
	{ id: "softirq", title: "Soft IRQ %", shortTitle: "Soft IRQ" }
] as const

type CpuMetricId = (typeof cpuMetrics)[number]["id"]

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

function formatMetricPercent(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return `${Number(value).toFixed(1)}%`
}

function usageColor(value: number | null | undefined): CardLinkColor | undefined {
	if (value === null || value === undefined) return undefined
	if (value >= 80) return "danger"
	if (value >= 50) return "warning"
	return "success"
}

const metricSeriesById = computed((): Record<CpuMetricId, TimeSeriesData | undefined> => ({
	system: cpu.cpu_usage_system,
	user: cpu.cpu_usage_user,
	iowait: cpu.cpu_iowait,
	softirq: cpu.cpu_softirq
}))

const statTiles = computed<CpuStatTile[]>(() =>
	cpuMetrics.map(metric => {
		const series = metricSeriesById.value[metric.id]
		const latest = latestSeriesValue(series)

		return {
			id: metric.id,
			title: metric.shortTitle,
			value: formatMetricPercent(latest),
			color: usageColor(latest)
		}
	})
)

const cpuCharts = computed<CpuChartConfig[]>(() =>
	cpuMetrics.map(metric => {
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
