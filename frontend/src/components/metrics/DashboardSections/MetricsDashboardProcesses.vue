<template>
	<n-spin :show="loading" class="min-h-40">
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
	</n-spin>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { ApiError } from "@/types/common.d"
import type { MetricsProcessesData, TimeSeriesData } from "@/types/metrics.d"
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
		title: "Processes",
		showTitle: true
	}
)

const message = useMessage()
const loading = ref(false)
const processes = ref<MetricsProcessesData>({})

async function reload() {
	loading.value = true
	try {
		const res = await Api.metrics.getProcesses(props.host, props.range)
		if (!res.data.success) {
			message.warning(res.data.message || "Error fetching process metrics")
			processes.value = {}
			return
		}
		processes.value = res.data.data || {}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Error fetching process metrics")
		processes.value = {}
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
		value: formatMetricNumber(processes.value.running),
		color: "success"
	},
	{
		id: "sleeping",
		title: "Sleeping",
		value: formatMetricNumber(processes.value.sleeping)
	},
	{
		id: "unknown",
		title: "Unknown",
		value: formatMetricNumber(processes.value.unknown),
		color: processes.value.unknown && processes.value.unknown > 0 ? "warning" : undefined
	},
	{
		id: "zombies",
		title: "Zombies",
		value: formatMetricNumber(processes.value.zombies),
		color: processes.value.zombies && processes.value.zombies > 0 ? "danger" : undefined
	}
])

const statusChart = computed(() => transformSeries(processes.value.status))
</script>
