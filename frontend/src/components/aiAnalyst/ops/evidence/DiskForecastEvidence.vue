<template>
	<div v-if="view" class="flex flex-col gap-3" data-testid="talon-ops-evidence-disk-forecast">
		<dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
			<dt class="text-secondary">Node</dt>
			<dd class="font-mono" data-testid="talon-ops-disk-node"><bdi>{{ view.node }}</bdi></dd>
			<dt class="text-secondary">Used</dt>
			<dd data-testid="talon-ops-disk-used">
				{{ gbText(view.usedGb) }} of {{ gbText(view.totalGb) }}
				<template v-if="view.usedPct !== null">({{ pctText(view.usedPct) }})</template>
			</dd>
			<dt class="text-secondary">Growth</dt>
			<dd data-testid="talon-ops-disk-slope">{{ gbPerDayText(view.slope) }}</dd>
			<template v-for="mark of view.watermarks" :key="mark.key">
				<dt class="text-secondary">{{ mark.label }}</dt>
				<dd :data-testid="`talon-ops-disk-${mark.key}`">
					{{ pctText(mark.pct) }}
					<template v-if="mark.bytes !== null">({{ bytesText(mark.bytes) }})</template>
					·
					<span v-if="mark.days === null" class="text-tertiary">not forecast</span>
					<span v-else-if="mark.days <= 0" class="text-warning">already there</span>
					<span v-else>in about {{ daysText(mark.days) }}</span>
				</dd>
			</template>
		</dl>

		<div v-if="isAdmin" class="flex flex-col gap-1">
			<div v-if="loading" class="flex justify-center py-4" data-testid="talon-ops-disk-loading"><n-spin size="small" /></div>
			<p v-else-if="failure" class="text-tertiary text-xs" data-testid="talon-ops-disk-error">
				The job's runs couldn't be read, so there is no chart: <bdi>{{ failure }}</bdi>
			</p>
			<template v-else-if="chart">
				<div class="text-secondary flex flex-wrap items-center gap-4 text-xs" role="list" aria-label="Legend">
					<span class="inline-flex items-center gap-1.5" role="listitem">
						<span class="inline-block h-0.5 w-4 rounded-sm" :style="{ backgroundColor: primary }" />
						Used, one sample a day
					</span>
					<span class="inline-flex items-center gap-1.5" role="listitem">
						<span class="inline-block w-4 border-t-2 border-dashed" :style="{ borderColor: primary }" />
						Projected at the slope
					</span>
				</div>
				<VChart
					class="w-full"
					autoresize
					:option="chart.option"
					:style="{ height: `${HEIGHT}px`, width: '100%' }"
					role="img"
					:aria-label="chart.summary"
					data-testid="talon-ops-disk-chart"
				/>
			</template>
			<p v-else class="text-tertiary text-xs" data-testid="talon-ops-disk-few">
				Fewer than two days of samples in the job's recent runs: the numbers only.
			</p>
		</div>
		<p v-else class="text-tertiary text-xs" data-testid="talon-ops-disk-admins-only">
			The chart reads the job's runs, which are for admins only.
		</p>

		<EvidenceFigures :items="view.figures" />
	</div>
</template>

<script setup lang="ts">
// `disk_forecast`: the node's disk in numbers (used, growth, each watermark and the days until it), and
// for an admin a chart of its daily used disk from the job's recent runs (`detail.nodes[node]`, one
// point per UTC day), the watermarks as lines and the slope projected out to the job's horizon. A
// platform job's runs are an admin's: anyone else sees the numbers only, and nothing is read for them.
import type { DiskPoint, Evidence } from "./evidence"
import type { TalonOpsRun } from "@/types/talonOps"
import { LineChart } from "echarts/charts"
import { GridComponent, MarkLineComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NSpin } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import VChart from "vue-echarts"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import { useSocChartColors } from "@/components/socManagement/charts/chart-colors"
import { useThemeStore } from "@/stores/theme"
import { buildDiskChart } from "./disk-chart"
import {
	bytesText,
	daysText,
	DISK_RUNS_LIMIT,
	diskForecastView,
	diskPoints,
	gbPerDayText,
	gbText,
	pctText,
	projectionDays
} from "./evidence"
import EvidenceFigures from "./EvidenceFigures.vue"

const {
	evidence,
	isAdmin = false,
	settings = null
} = defineProps<{ evidence: Evidence | null; isAdmin?: boolean; settings?: Record<string, unknown> | null }>()

use([CanvasRenderer, LineChart, GridComponent, MarkLineComponent, TooltipComponent])

const HEIGHT = 220
const theme = useThemeStore()
const { primary } = useSocChartColors()

const view = computed(() => diskForecastView(evidence))
const runs = ref<TalonOpsRun[]>([])
const loading = ref(false)
const failure = ref<string | null>(null)
let controller: AbortController | null = null

const points = computed<DiskPoint[]>(() => (view.value ? diskPoints(runs.value, view.value.node) : []))
const chart = computed(() =>
	view.value
		? buildDiskChart(
				view.value,
				points.value,
				projectionDays(settings, view.value),
				{
					primary: primary.value,
					warning: theme.style["warning-color"] ?? "#FFB600",
					error: theme.style["error-color"] ?? "#FF0156"
				},
				theme.style
			)
		: null
)

async function load() {
	controller?.abort()
	runs.value = []
	failure.value = null
	if (!isAdmin || !view.value) return
	const own = new AbortController()
	controller = own
	loading.value = true
	try {
		const { data } = await Api.talonOps.listRuns({ job: "disk_forecast", limit: DISK_RUNS_LIMIT }, own.signal)
		if (controller !== own) return
		runs.value = Array.isArray(data?.items) ? data.items : []
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		failure.value = opsFailure(err).detail
	} finally {
		if (controller === own) loading.value = false
	}
}

watch(() => [isAdmin, view.value?.node], load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>
