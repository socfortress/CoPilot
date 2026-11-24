<template>
	<!--
		The account's failures across its completed scans: a stacked column per scan (trend.ts), or the
		same numbers as a table. Either way a scan opens below when picked, as from the scans list.
	-->
	<section class="border-default bg-default overflow-hidden rounded-lg border" data-testid="cloud-trend">
		<header
			class="bg-secondary border-default flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2"
		>
			<span :class="SECTION_LABEL">Failures over time</span>
			<div class="flex items-center gap-3">
				<span class="text-secondary text-2xs font-mono tabular-nums">{{ points.length }} completed scans</span>
				<SegmentedToggle v-model="view" :options="VIEWS" label="Show" test-id="cloud-trend-view" />
			</div>
		</header>

		<div v-if="view === 'chart'" class="flex flex-col gap-2 px-4 pt-3 pb-2">
			<ul
				class="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-xs"
				aria-label="Severities"
				data-testid="cloud-trend-legend"
			>
				<li
					v-for="severity of severities"
					:key="severity"
					class="text-secondary inline-flex items-center gap-1.5"
				>
					<span class="inline-block size-2.5 rounded-xs" :style="{ backgroundColor: colors[severity] }" />
					{{ SEVERITY_LABELS[severity] }}
				</li>
			</ul>
			<CloudFailuresTrendChart :points :selected-id @select="emit('select', $event)" />
			<p class="text-tertiary m-0 text-xs">
				Unmuted failures of each completed scan. Click a column to open its scan.
			</p>
		</div>

		<div v-else class="overflow-x-auto">
			<table class="w-full border-collapse text-sm" data-testid="cloud-trend-table">
				<thead>
					<tr class="border-default text-secondary border-b text-left text-xs">
						<th scope="col" class="px-4 py-2 font-medium">Scan</th>
						<th scope="col" class="px-3 py-2 font-medium">Completed</th>
						<th
							v-for="severity of severities"
							:key="severity"
							scope="col"
							class="px-3 py-2 text-right font-medium"
						>
							{{ SEVERITY_LABELS[severity] }}
						</th>
						<th scope="col" class="px-3 py-2 text-right font-medium">Failed</th>
						<th scope="col" class="px-4 py-2 font-medium">Since the scan before</th>
					</tr>
				</thead>
				<tbody class="divide-border divide-y">
					<tr
						v-for="point of rows"
						:key="point.id"
						:class="point.id === selectedId ? 'bg-secondary/40' : ''"
						:data-testid="`cloud-trend-row-${point.id}`"
					>
						<td
							class="border-l-2 px-4 py-1.5"
							:class="point.id === selectedId ? 'border-l-primary' : 'border-l-transparent'"
						>
							<button
								type="button"
								class="text-primary font-mono text-xs hover:underline"
								:aria-current="point.id === selectedId ? 'true' : undefined"
								@click="emit('select', point.id)"
							>
								#{{ point.id }}
							</button>
						</td>
						<td class="text-secondary px-3 py-1.5 text-xs whitespace-nowrap">{{ when(point.at) }}</td>
						<td
							v-for="severity of severities"
							:key="severity"
							class="px-3 py-1.5 text-right font-mono text-xs tabular-nums"
							:class="point.bySeverity[severity] ? 'text-default' : 'text-tertiary'"
						>
							{{ point.bySeverity[severity].toLocaleString() }}
						</td>
						<td class="text-default px-3 py-1.5 text-right font-mono text-xs font-semibold tabular-nums">
							{{ point.failed.toLocaleString() }}
						</td>
						<td class="text-secondary px-4 py-1.5 text-xs whitespace-nowrap">{{ changeText(point) }}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { TrendPoint } from "./trend"
import { computed, ref } from "vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import { useSettingsStore } from "@/stores/settings"
import { useThemeStore } from "@/stores/theme"
import { formatDate } from "@/utils/format"
import CloudFailuresTrendChart from "./CloudFailuresTrendChart.vue"
import { changeText, TREND_COLORS, trendSeverities } from "./trend"
import { SEVERITY_LABELS } from "./utils"

const { points, selectedId } = defineProps<{ points: TrendPoint[]; selectedId: number | null }>()
const emit = defineEmits<{ (e: "select", scanId: number): void }>()

const VIEWS: { value: "chart" | "table"; label: string }[] = [
	{ value: "chart", label: "Chart" },
	{ value: "table", label: "Table" }
]

const theme = useThemeStore()
const dFormats = useSettingsStore().dateFormat
const view = ref<"chart" | "table">("chart")

const severities = computed(() => trendSeverities(points))
const colors = computed(() => TREND_COLORS[theme.isThemeDark ? "dark" : "light"])
/** Newest first, as the scans list below. */
const rows = computed(() => [...points].reverse())

function when(at: string): string {
	return at ? String(formatDate(at, dFormats.datetime)) : "—"
}
</script>
