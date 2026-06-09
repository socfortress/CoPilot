<template>
	<section class="@container flex flex-col gap-4">
		<div v-if="shouldShowSectionTitle">
			<h3 class="text-lg font-semibold">{{ title }}</h3>
		</div>

		<div class="grid grid-cols-1 gap-3 @md:grid-cols-2 @3xl:grid-cols-4 @7xl:grid-cols-6">
			<CardLink
				v-for="tile in statTiles"
				:key="tile.id"
				size="small"
				:title="tile.title"
				:value="tile.value"
				:color="tile.color"
			/>
		</div>

		<div class="grid grid-cols-1 gap-4 @lg:grid-cols-3">
			<CardEntity size="small" main-box-class="gap-0">
				<template #headerMain>
					<span class="text-secondary text-xs font-medium uppercase">CPU Idle</span>
				</template>
				<template #default>
					<ChartGauge :value="cpuIdle" :height="220" />
				</template>
			</CardEntity>

			<CardEntity size="small" card-entity-class="@lg:col-span-2" main-box-class="gap-0">
				<template #headerMain>
					<span class="text-secondary text-xs font-medium uppercase">System Load</span>
				</template>
				<template #default>
					<ChartArea
						:labels="loadLabels"
						:data="loadData"
						:series-names="loadSeriesNames"
						labels-datetime
						:height="220"
					/>
				</template>
			</CardEntity>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { MetricsSummaryData } from "@/types/metrics.d"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"
import ChartGauge from "@/components/common/charts/ChartGauge.vue"
import { formatBytes } from "@/utils/format"

const props = withDefaults(
	defineProps<{
		summary: MetricsSummaryData
		title?: string
		showTitle?: boolean
	}>(),
	{
		title: "Metrics Summary",
		showTitle: true
	}
)

const shouldShowSectionTitle = computed(() => props.showTitle && Boolean(props.title.trim()))

const cpuIdle = computed(() => props.summary.cpu_idle ?? 0)

const loadLabels = computed(() => {
	const load = props.summary.load ?? {}
	const firstSeries = Object.values(load)[0]
	return firstSeries?.map(point => point.time) ?? []
})

const loadData = computed(() => {
	const load = props.summary.load ?? {}
	const rows = Object.values(load).map(points => points.map(point => point.value))
	if (rows.length <= 1) return rows[0] ?? []
	return rows
})

const loadSeriesNames = computed(() => Object.keys(props.summary.load ?? {}))

interface SummaryStatTile {
	id: string
	title: string
	value: string
	color?: CardLinkColor
}

const statTiles = computed<SummaryStatTile[]>(() => [
	{
		id: "uptime",
		title: "Uptime",
		value: formatUptime(props.summary.uptime),
		color: "primary"
	},
	{
		id: "total-mem",
		title: "Total Memory",
		value: formatMetricBytes(props.summary.total_mem)
	},
	{
		id: "cpus",
		title: "CPUs",
		value: formatMetricNumber(props.summary.cpus)
	},
	{
		id: "processes",
		title: "Processes",
		value: formatMetricNumber(props.summary.total_processes)
	},
	{
		id: "swap-free",
		title: "Swap Free",
		value: formatMetricBytes(props.summary.swap_free)
	},
	{
		id: "users",
		title: "Users Logged In",
		value: formatMetricNumber(props.summary.logged_on_users)
	}
])

function formatMetricNumber(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return Number(value).toLocaleString()
}

function formatMetricBytes(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return formatBytes(value) ?? "—"
}

function formatUptime(seconds: number | null | undefined): string {
	if (seconds === null || seconds === undefined) return "—"
	const total = Number(seconds)
	const d = Math.floor(total / 86400)
	const h = Math.floor((total % 86400) / 3600)
	const m = Math.floor((total % 3600) / 60)
	if (d > 0) return `${d}d ${h}h ${m}m`
	if (h > 0) return `${h}h ${m}m`
	return `${m}m`
}
</script>
