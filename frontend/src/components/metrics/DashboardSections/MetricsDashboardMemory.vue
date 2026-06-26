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
	</n-spin>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { ApiError } from "@/types/common"
import type { MetricsMemoryData, TimeSeriesData } from "@/types/metrics"
import { NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"
import { getApiErrorMessage } from "@/utils"
import { formatBytes } from "@/utils/format"

const props = withDefaults(
	defineProps<{
		host: string
		range: string
		title?: string
		showTitle?: boolean
	}>(),
	{
		title: "Memory",
		showTitle: true
	}
)

const message = useMessage()
const loading = ref(false)
const memory = ref<MetricsMemoryData>({})

async function reload() {
	loading.value = true
	try {
		const res = await Api.metrics.getMemory(props.host, props.range)
		if (!res.data.success) {
			message.warning(res.data.message || "Error fetching memory metrics")
			memory.value = {}
			return
		}
		memory.value = res.data.data || {}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Error fetching memory metrics")
		memory.value = {}
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

function swapFreeColor(
	swapFree: number | null | undefined,
	swapTotal: number | null | undefined
): CardLinkColor | undefined {
	if (
		swapFree === null ||
		swapFree === undefined ||
		swapTotal === null ||
		swapTotal === undefined ||
		swapTotal <= 0
	) {
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
		value: formatMetricBytes(memory.value.swap_total),
		color: "primary"
	},
	{
		id: "swap-free",
		title: "Swap Free",
		value: formatMetricBytes(memory.value.swap_free),
		color: swapFreeColor(memory.value.swap_free, memory.value.swap_total)
	}
])

const memUsedChart = computed(() => transformSeries(memory.value.mem_used))
</script>
