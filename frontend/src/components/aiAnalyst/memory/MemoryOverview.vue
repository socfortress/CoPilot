<template>
	<div class="flex flex-col gap-4" data-testid="talon-memory-overview">
		<div v-if="!stats && loading" class="flex justify-center py-10" data-testid="talon-memory-stats-loading">
			<n-spin size="small" />
		</div>
		<MemoryProblem v-else-if="problem" :state="problem" @retry="emit('retry')" />

		<template v-if="stats">
			<div
				class="bg-border border-default grid grid-cols-1 gap-px overflow-hidden rounded-lg border sm:grid-cols-3"
				:class="{ 'opacity-60': loading }"
				data-testid="talon-memory-tiles"
			>
				<KpiTile
					label="Memories"
					:value="formatCount(stats.total)"
					help="Every drawer Talon keeps for this customer, from investigations, reviews and chat."
					:hint="checked"
					test-id="talon-memory-total"
				/>
				<KpiTile
					label="Filed, last 30 days"
					:value="formatCount(filed)"
					help="Memories Talon filed for this customer in the last 30 days (UTC)."
					test-id="talon-memory-filed"
				/>
				<KpiTile
					label="Hidden from investigations"
					:value="formatCount(stats.testing_hidden)"
					help="Lessons kept but not used by new investigations because they came from testing. Testing is never a reason to lower an alert's severity."
					hint="kept, not used"
					test-id="talon-memory-hidden"
				/>
			</div>

			<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
				<SocPanel title="Filed per day" caption="last 30 days, UTC" class="xl:col-span-3">
					<VChart
						v-if="growthOption"
						class="w-full"
						autoresize
						:option="growthOption"
						:style="{ height: '180px', width: '100%' }"
						role="img"
						:aria-label="growthSummary(stats)"
						data-testid="talon-memory-growth"
					/>
					<n-empty
						v-else
						description="Talon reported no growth data"
						class="py-6"
						data-testid="talon-memory-growth-empty"
					/>
					<n-collapse v-if="stats.growth.length" class="mt-2">
						<n-collapse-item title="Show the numbers" name="growth">
							<n-table size="small" :bordered="false" data-testid="talon-memory-growth-table">
								<thead>
									<tr>
										<th>Day (UTC)</th>
										<th class="text-right">Filed</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="day of stats.growth" :key="day.date">
										<td>{{ day.date }}</td>
										<td class="text-right font-mono">{{ formatCount(day.filed) }}</td>
									</tr>
								</tbody>
							</n-table>
						</n-collapse-item>
					</n-collapse>
				</SocPanel>

				<SocPanel
					v-for="panel of panels"
					:key="panel.id"
					:title="panel.title"
					caption="select a row to filter"
					:class="{ 'xl:col-span-2': panel.id === 'rooms' }"
				>
					<table class="w-full text-sm" :data-testid="`talon-memory-${panel.id}`">
						<caption class="sr-only">{{ panel.title }}: memories per {{ panel.unit }}</caption>
						<tbody>
							<tr v-for="row of panel.rows" :key="row.key" :data-key="row.key">
								<th scope="row" class="w-40 py-1 pr-3 text-left font-normal">
									<button
										type="button"
										class="text-default hover:text-primary focus-visible:text-primary cursor-pointer text-left underline-offset-2 hover:underline"
										:title="row.hint"
										:aria-label="`${row.label}: ${formatCount(row.count)}. Show only these`"
										:data-testid="`talon-memory-${panel.id}-filter`"
										@click="emit('filter', panel.id === 'rooms' ? 'room' : 'source', row.key)"
									>
										{{ row.label }}
									</button>
								</th>
								<td class="py-1" aria-hidden="true">
									<div class="bg-secondary h-2.5 w-full rounded-sm">
										<div
											class="h-2.5 rounded-r-sm"
											:style="{
												width: `${Math.max(row.count ? 1 : 0, row.share * 100)}%`,
												backgroundColor: barColor
											}"
										/>
									</div>
								</td>
								<td class="w-20 py-1 pl-3 text-right font-mono tabular-nums">
									{{ formatCount(row.count) }}
								</td>
							</tr>
						</tbody>
					</table>
				</SocPanel>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
// The Memory tab's summary for one customer: three tiles, memories filed per day, and the room and
// source breakdowns (labelled bars; choosing a row filters the drawer list). The data comes from the
// parent (one `GET …/stats` per customer), so a refresh dims rather than blanks.
import type { ProblemState } from "./memory"
import type { TalonMemoryStats } from "@/types/talonMemory"
import { BarChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NCollapse, NCollapseItem, NEmpty, NSpin, NTable } from "naive-ui"
import { computed } from "vue"
import VChart from "vue-echarts"
import KpiTile from "@/components/socManagement/ui/KpiTile.vue"
import SocPanel from "@/components/socManagement/ui/SocPanel.vue"
import { useThemeStore } from "@/stores/theme"
import { formatTime } from "../health/health"
import {
	breakdown,
	buildGrowthOption,
	formatCount,
	growthSummary,
	growthTotal,
	MEMORY_CHART_COLORS,
	ROOMS,
	SOURCES
} from "./memory"
import MemoryProblem from "./MemoryProblem.vue"

const {
	stats,
	loading = false,
	problem = null
} = defineProps<{
	stats: TalonMemoryStats | null
	loading?: boolean
	problem?: ProblemState | null
}>()
const emit = defineEmits<{
	(e: "filter", kind: "room" | "source", value: string): void
	(e: "retry"): void
}>()

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])
const theme = useThemeStore()

const filed = computed(() => growthTotal(stats))
const checked = computed(() => (stats?.checked_at ? `as of ${formatTime(stats.checked_at)}` : undefined))
const growthOption = computed(() => buildGrowthOption(stats, theme.style, theme.isThemeDark))
const barColor = computed(() => MEMORY_CHART_COLORS[theme.isThemeDark ? "dark" : "light"])
const panels = computed(() => [
	{ id: "rooms", title: "By room", unit: "room", rows: breakdown(stats?.rooms, ROOMS) },
	{ id: "sources", title: "By source", unit: "source", rows: breakdown(stats?.sources, SOURCES) }
])
</script>
