<template>
	<section class="@container flex flex-col gap-4">
		<div v-if="shouldShowSectionTitle">
			<h3 class="text-lg font-semibold">{{ title }}</h3>
		</div>

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

		<CardEntity size="small" main-box-class="gap-0">
			<template #headerMain>
				<span class="text-secondary text-xs font-medium uppercase">Process Status</span>
			</template>
			<template #default>
				<ChartArea
					:labels="statusChart.labels"
					:data="statusChart.data"
					:series-names="statusChart.seriesNames"
					labels-datetime
					:height="220"
				/>
			</template>
		</CardEntity>
	</section>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { MetricsProcessesData, TimeSeriesData } from "@/types/metrics.d"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"

const props = withDefaults(
	defineProps<{
		processes: MetricsProcessesData
		title?: string
		showTitle?: boolean
	}>(),
	{
		title: "Processes",
		showTitle: true
	}
)

const shouldShowSectionTitle = computed(() => props.showTitle && Boolean(props.title.trim()))

interface ProcessStatTile {
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

function formatMetricNumber(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return Number(value).toLocaleString()
}

const statTiles = computed<ProcessStatTile[]>(() => [
	{
		id: "running",
		title: "Running",
		value: formatMetricNumber(props.processes.running),
		color: "success"
	},
	{
		id: "sleeping",
		title: "Sleeping",
		value: formatMetricNumber(props.processes.sleeping)
	},
	{
		id: "unknown",
		title: "Unknown",
		value: formatMetricNumber(props.processes.unknown),
		color: props.processes.unknown && props.processes.unknown > 0 ? "warning" : undefined
	},
	{
		id: "zombies",
		title: "Zombies",
		value: formatMetricNumber(props.processes.zombies),
		color: props.processes.zombies && props.processes.zombies > 0 ? "danger" : undefined
	}
])

const statusChart = computed(() => transformSeries(props.processes.status))
</script>
