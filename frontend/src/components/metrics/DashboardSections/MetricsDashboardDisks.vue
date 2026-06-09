<template>
	<section class="@container flex flex-col gap-4">
		<div v-if="shouldShowSectionTitle">
			<h3 class="text-lg font-semibold">{{ title }}</h3>
		</div>

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
			<CardEntity v-for="chart in diskCharts" :key="chart.id" size="small" main-box-class="gap-0">
				<template #headerMain>
					<span class="text-secondary text-xs font-medium uppercase">{{ chart.title }}</span>
				</template>
				<template #default>
					<ChartArea
						:labels="chart.labels"
						:data="chart.data"
						:series-names="chart.seriesNames"
						labels-datetime
						:y-axis-name="chart.yAxisName"
						:use-format-bytes="chart.useFormatBytes"
						:height="220"
					/>
				</template>
			</CardEntity>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { MetricsDisksData, TimeSeriesData } from "@/types/metrics.d"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"
import { formatBytes } from "@/utils/format"

const props = withDefaults(
	defineProps<{
		disks: MetricsDisksData
		title?: string
		showTitle?: boolean
	}>(),
	{
		title: "Disks",
		showTitle: true
	}
)

const shouldShowSectionTitle = computed(() => props.showTitle && Boolean(props.title.trim()))

interface DiskStatTile {
	id: string
	title: string
	value: string
	color?: CardLinkColor
}

interface DiskChartConfig {
	id: string
	title: string
	labels: string[]
	data: number[] | number[][]
	seriesNames: string[]
	yAxisName?: string
	useFormatBytes?: boolean
}

const diskChartsConfig = [
	{ id: "usage", title: "Disk Usage %", yAxisName: "%" },
	{ id: "io", title: "Disk I/O (bytes/s)", yAxisName: "B/s", useFormatBytes: true }
] as const

type DiskChartId = (typeof diskChartsConfig)[number]["id"]

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

function formatMetricBytes(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return formatBytes(value) ?? "—"
}

function formatMetricPercent(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return `${Number(value).toFixed(1)}%`
}

function usageColor(value: number | null | undefined): CardLinkColor | undefined {
	if (value === null || value === undefined) return undefined
	if (value >= 90) return "danger"
	if (value >= 75) return "warning"
	return "success"
}

const metricSeriesById = computed((): Record<DiskChartId, TimeSeriesData | undefined> => ({
	usage: props.disks.disk_usage,
	io: props.disks.disk_io
}))

const statTiles = computed<DiskStatTile[]>(() => [
	{
		id: "disk-total",
		title: "Total Disk Size",
		value: formatMetricBytes(props.disks.disk_total),
		color: "primary"
	},
	{
		id: "disk-usage",
		title: "Disk Usage",
		value: formatMetricPercent(latestSeriesValue(props.disks.disk_usage)),
		color: usageColor(latestSeriesValue(props.disks.disk_usage))
	}
])

const diskCharts = computed<DiskChartConfig[]>(() =>
	diskChartsConfig.map(metric => {
		const series = metricSeriesById.value[metric.id]
		const transformed = transformSeries(series)

		return {
			id: metric.id,
			title: metric.title,
			yAxisName: metric.yAxisName,
			useFormatBytes: "useFormatBytes" in metric ? metric.useFormatBytes : false,
			...transformed
		}
	})
)
</script>
