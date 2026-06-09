<template>
	<n-spin :show="loading" class="min-h-40">
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
				<CardEntity v-for="chart in networkCharts" :key="chart.id" size="small" main-box-class="gap-0">
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
	</n-spin>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { ApiError } from "@/types/common.d"
import type { MetricsNetworkData, TimeSeriesData } from "@/types/metrics.d"
import { NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"
import { getApiErrorMessage } from "@/utils"

const props = withDefaults(
	defineProps<{
		host: string
		range: string
		title?: string
		showTitle?: boolean
	}>(),
	{
		title: "Network",
		showTitle: true
	}
)

const message = useMessage()
const loading = ref(false)
const network = ref<MetricsNetworkData>({})

async function reload() {
	loading.value = true
	try {
		const res = await Api.metrics.getNetwork(props.host, props.range)
		if (!res.data.success) {
			message.warning(res.data.message || "Error fetching network metrics")
			network.value = {}
			return
		}
		network.value = res.data.data || {}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as ApiError) || "Error fetching network metrics")
		network.value = {}
	} finally {
		loading.value = false
	}
}

watch(
	() => [props.host, props.range] as const,
	() => reload(),
	{ immediate: true }
)

defineExpose({ reload })

const shouldShowSectionTitle = computed(() => props.showTitle && Boolean(props.title.trim()))

interface NetworkStatTile {
	id: string
	title: string
	value: string
	color?: CardLinkColor
}

interface NetworkChartConfig {
	id: string
	title: string
	labels: string[]
	data: number[] | number[][]
	seriesNames: string[]
	yAxisName?: string
	useFormatBytes?: boolean
}

const networkChartsConfig = [
	{ id: "traffic", title: "Network Traffic (bytes/s)", yAxisName: "B/s", useFormatBytes: true },
	{ id: "errors", title: "Interface Errors" }
] as const

type NetworkChartId = (typeof networkChartsConfig)[number]["id"]

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

function formatMetricNumber(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—"
	return Number(value).toLocaleString()
}

function errorsColor(value: number | null | undefined): CardLinkColor | undefined {
	if (value === null || value === undefined || value <= 0) return undefined
	if (value >= 100) return "danger"
	return "warning"
}

const metricSeriesById = computed(
	(): Record<NetworkChartId, TimeSeriesData | undefined> => ({
		traffic: network.value.traffic,
		errors: network.value.interface_errors
	})
)

const statTiles = computed<NetworkStatTile[]>(() => [
	{
		id: "tcp-established",
		title: "TCP Sessions Established",
		value: formatMetricNumber(network.value.tcp_established),
		color: "primary"
	},
	{
		id: "interface-errors",
		title: "Interface Errors",
		value: formatMetricNumber(latestSeriesValue(network.value.interface_errors)),
		color: errorsColor(latestSeriesValue(network.value.interface_errors))
	}
])

const networkCharts = computed<NetworkChartConfig[]>(() =>
	networkChartsConfig.map(metric => {
		const series = metricSeriesById.value[metric.id]
		const transformed = transformSeries(series)

		return {
			id: metric.id,
			title: metric.title,
			yAxisName: "yAxisName" in metric ? metric.yAxisName : undefined,
			useFormatBytes: "useFormatBytes" in metric ? metric.useFormatBytes : false,
			...transformed
		}
	})
)
</script>
