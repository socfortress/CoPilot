<template>
	<div class="flex flex-col gap-4" data-testid="talon-health-charts">
		<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			<div
				v-for="item of charts"
				:key="item.id"
				class="border-default flex flex-col gap-2 rounded-lg border p-3"
				:data-testid="`talon-health-chart-${item.id}`"
			>
				<div class="flex flex-wrap items-center justify-between gap-2">
					<span :class="SECTION_LABEL">{{ item.title }}</span>
					<n-button
						v-if="item.id === 'cost' && usageAvailable"
						text
						size="tiny"
						type="primary"
						data-testid="talon-health-usage-link"
						@click="emit('open-usage')"
					>
						Open the Usage tab
						<template #icon><Icon name="carbon:arrow-right" :size="12" /></template>
					</n-button>
				</div>
				<div
					v-if="item.legend.length"
					class="text-secondary flex flex-wrap items-center gap-4 text-xs"
					role="list"
					aria-label="Legend"
				>
					<span
						v-for="entry of item.legend"
						:key="entry.name"
						class="inline-flex items-center gap-1.5"
						role="listitem"
					>
						<span
							class="inline-block rounded-sm"
							:class="entry.kind === 'line' ? 'h-0.5 w-4' : 'h-2.5 w-2.5'"
							:style="{ backgroundColor: entry.color }"
						/>
						{{ entry.name }}
					</span>
				</div>
				<p
					v-for="note of item.notes"
					:key="note"
					class="text-tertiary text-xs"
					data-testid="talon-health-chart-note"
				>
					{{ note }}
				</p>
				<VChart
					v-if="item.option"
					class="w-full"
					autoresize
					:option="item.option"
					:style="{ height: `${HEIGHT}px`, width: '100%' }"
					role="img"
					:aria-label="item.summary"
				/>
				<div
					v-else
					class="text-tertiary flex items-center justify-center text-sm"
					:style="{ height: `${HEIGHT}px` }"
					data-testid="talon-health-chart-no-data"
				>
					No data
				</div>
			</div>
		</div>

		<n-collapse>
			<n-collapse-item title="Show the numbers" name="table">
				<div class="overflow-x-auto">
					<n-table size="small" :bordered="false" data-testid="talon-health-metrics-table">
						<thead>
							<tr>
								<th>Bucket</th>
								<th class="text-right">Completed</th>
								<th class="text-right">Failed</th>
								<th class="text-right">Duration p50</th>
								<th class="text-right">Duration p95</th>
								<th class="text-right">Queued (max)</th>
								<th class="text-right">Tool calls (investigations)</th>
								<th class="text-right">Tool errors</th>
								<th
									class="text-right"
									title="Failed model calls Talon recorded; there may have been more"
								>
									Model errors (at least)
								</th>
								<th class="text-right">Cost (USD)</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(bucket, index) of series" :key="index" data-testid="talon-health-metrics-row">
								<td class="whitespace-nowrap">{{ formatTime(bucket.t) }}</td>
								<td class="text-right font-mono">{{ formatCount(bucket.investigations_completed) }}</td>
								<td class="text-right font-mono">{{ formatCount(bucket.investigations_failed) }}</td>
								<td class="text-right font-mono">{{ formatSeconds(bucket.duration_p50_s) }}</td>
								<td class="text-right font-mono">{{ formatSeconds(bucket.duration_p95_s) }}</td>
								<td class="text-right font-mono">{{ formatCount(bucket.queue_depth_max) }}</td>
								<td class="text-right font-mono">{{ formatCount(bucket.tool_calls) }}</td>
								<td class="text-right font-mono">{{ formatCount(bucket.tool_errors) }}</td>
								<td class="text-right font-mono">{{ formatCount(bucket.model_errors) }}</td>
								<td class="text-right font-mono">{{ bucket.cost_usd ?? NO_DATA }}</td>
							</tr>
						</tbody>
					</n-table>
				</div>
			</n-collapse-item>
		</n-collapse>
	</div>
</template>

<script setup lang="ts">
// The dashboard's charts (their options and design notes: ./health-charts.ts) and their table
// view, every figure as talon-analyst sent it ("no data" for a null, the cost as its string).
import type { TalonMetricsBucket } from "@/types/talonHealth"
import { BarChart, LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NButton, NCollapse, NCollapseItem, NTable } from "naive-ui"
import { computed } from "vue"
import VChart from "vue-echarts"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSocChartColors } from "@/components/socManagement/charts/chart-colors"
import { useThemeStore } from "@/stores/theme"
import { formatCount, formatSeconds, formatTime, NO_DATA } from "./health"
import { buildHealthCharts } from "./health-charts"

const {
	series,
	hours,
	usageAvailable = false
} = defineProps<{
	series: TalonMetricsBucket[]
	hours: number
	usageAvailable?: boolean
}>()
const emit = defineEmits<{ (e: "open-usage"): void }>()

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent])

const HEIGHT = 200
const theme = useThemeStore()
const { primary, secondary } = useSocChartColors()

const charts = computed(() =>
	buildHealthCharts(
		series,
		hours,
		{ primary: primary.value, secondary: secondary.value, error: theme.style["error-color"] ?? "#FF0156" },
		theme.style
	)
)
</script>
