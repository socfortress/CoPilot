<template>
	<n-spin :show="loading" class="min-h-40">
		<section class="@container flex flex-col gap-4">
			<div v-if="shouldShowSectionTitle">
				<h3 class="text-lg font-semibold">{{ title }}</h3>
			</div>

			<div class="grid grid-cols-1 gap-3 @md:grid-cols-2 @3xl:grid-cols-3 @7xl:grid-cols-6">
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
	</n-spin>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { ApiError } from "@/types/common.d"
import type { MetricsSummaryData } from "@/types/metrics.d"
import { NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartArea from "@/components/common/charts/ChartArea.vue"
import ChartGauge from "@/components/common/charts/ChartGauge.vue"
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
		title: "Metrics Summary",
		showTitle: true
	}
)

const message = useMessage()
const loading = ref(false)
const summary = ref<MetricsSummaryData>({})

async function reload() {
	loading.value = true
	try {
		const res = await Api.metrics.getSummary(props.host, props.range)
		if (!res.data.success) {
			message.warning(res.data.message || "Error fetching summary metrics")
			summary.value = {}
			return
		}
		summary.value = res.data.data || {}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as ApiError) || "Error fetching summary metrics")
		summary.value = {}
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

const cpuIdle = computed(() => summary.value.cpu_idle ?? 0)

const loadLabels = computed(() => {
	const load = summary.value.load ?? {}
	const firstSeries = Object.values(load)[0]
	return firstSeries?.map(point => point.time) ?? []
})

const loadData = computed(() => {
	const load = summary.value.load ?? {}
	const rows = Object.values(load).map(points => points.map(point => point.value))
	if (rows.length <= 1) return rows[0] ?? []
	return rows
})

const loadSeriesNames = computed(() => Object.keys(summary.value.load ?? {}))

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
		value: formatUptime(summary.value.uptime),
		color: "primary"
	},
	{
		id: "total-mem",
		title: "Total Memory",
		value: formatMetricBytes(summary.value.total_mem)
	},
	{
		id: "cpus",
		title: "CPUs",
		value: formatMetricNumber(summary.value.cpus)
	},
	{
		id: "processes",
		title: "Processes",
		value: formatMetricNumber(summary.value.total_processes)
	},
	{
		id: "swap-free",
		title: "Swap Free",
		value: formatMetricBytes(summary.value.swap_free)
	},
	{
		id: "users",
		title: "Users Logged In",
		value: formatMetricNumber(summary.value.logged_on_users)
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
