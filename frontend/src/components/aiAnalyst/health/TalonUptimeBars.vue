<template>
	<div class="flex flex-col gap-3" data-testid="talon-uptime">
		<div class="text-secondary flex flex-wrap items-center gap-4 text-xs" role="list" aria-label="Legend">
			<span v-for="item of legend" :key="item.status" class="inline-flex items-center gap-1.5" role="listitem">
				<span class="uptime-key" :class="`cell-${item.status}`" :style="{ backgroundColor: cellColor(item.status) }" />
				{{ item.label }}
			</span>
			<span v-if="barText" class="text-tertiary" data-testid="talon-uptime-bar-size">{{ barText }}</span>
		</div>
		<div v-if="rows.length" class="flex flex-col gap-2">
			<div
				v-for="row of rows"
				:key="row.id"
				class="grid grid-cols-[minmax(8rem,12rem)_1fr_9rem] items-center gap-3"
				data-testid="talon-uptime-row"
				:data-component="row.id"
			>
				<span class="truncate text-sm" :title="row.name"><bdi>{{ row.name }}</bdi></span>
				<div
					v-if="row.cells.length"
					class="flex h-6 items-end gap-px"
					role="img"
					:aria-label="`${row.name}: ${row.summary}`"
				>
					<span
						v-for="(cell, index) of row.cells"
						:key="index"
						class="uptime-cell"
						:class="`cell-${cell.status}`"
						:style="{ backgroundColor: cellColor(cell.status) }"
						:title="cellTitle(cell)"
						:data-status="cell.status"
					/>
				</div>
				<span v-else class="text-tertiary text-xs">no data</span>
				<span class="text-secondary text-right text-xs whitespace-nowrap" data-testid="talon-uptime-summary">
					{{ row.summary }}
				</span>
			</div>
		</div>
		<n-empty v-else description="No history yet" class="py-6" data-testid="talon-uptime-empty" />
	</div>
</template>

<script setup lang="ts">
// Uptime bars: one row per component, one bar per bucket coloured by its worst status, with a
// height that steps with severity (no data 25%, OK 50%, warning 75%, failing full), so a problem
// stands out without colour too. A bucket with nothing counted is no data (talon-analyst doesn't
// count "off" probes). Each row also says it in words ("2 failing of 24"); each bar's
// title gives its time and counts. More buckets than fit (a week of 5-minute ones) merge, keeping
// the worst status (`uptimeCells`).
import type { CellStatus, UptimeCell } from "./health"
import type { TalonHealthComponent, TalonHistoryData } from "@/types/talonHealth"
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import { TONE_COLOR } from "@/components/socManagement/utils"
import { formatTime, uptimeCells, uptimeSummary } from "./health"

const { components, history, hours } = defineProps<{
	components: TalonHealthComponent[]
	history: TalonHistoryData
	hours: number
}>()

const legend: { status: CellStatus; label: string }[] = [
	{ status: "ok", label: "OK" },
	{ status: "warn", label: "Warning" },
	{ status: "fail", label: "Failing" },
	{ status: "none", label: "No data" }
]

function cellColor(status: CellStatus) {
	if (status === "ok") return TONE_COLOR.good
	if (status === "warn") return TONE_COLOR.warn
	if (status === "fail") return TONE_COLOR.bad
	return "var(--border-color)"
}

function cellTitle(cell: UptimeCell) {
	const when = cell.start === cell.end ? formatTime(cell.start) : `${formatTime(cell.start)} – ${formatTime(cell.end)}`
	const word = legend.find(l => l.status === cell.status)?.label ?? ""
	return `${when}: ${word} (ok ${cell.ok}, warning ${cell.warn}, failing ${cell.fail})`
}

const maxCells = computed(() => (hours > 24 ? 168 : 96))

/** What one bar covers: talon-analyst's bucket, times the buckets merged into a bar. */
const barText = computed(() => {
	const minutes = history?.bucket_minutes
	const longest = Math.max(0, ...Object.values(history?.components ?? {}).map(b => (Array.isArray(b) ? b.length : 0)))
	if (typeof minutes !== "number" || !longest) return null
	const bar = minutes * Math.max(1, Math.ceil(longest / maxCells.value))
	return `each bar ${bar % 60 === 0 ? `${bar / 60} h` : `${bar} min`}`
})

const rows = computed(() => {
	const byId = history?.components && typeof history.components === "object" ? history.components : {}
	// The components' own order first (as the grid shows them), then any id only history knows.
	const ids = [...components.map(c => c.id), ...Object.keys(byId).filter(id => !components.some(c => c.id === id))]
	return ids
		.filter(id => id in byId)
		.map(id => {
			// 7 d is 168 hourly buckets, one bar each; 24 h is 288 five-minute ones, 96 bars of 15 min.
			const cells = uptimeCells(byId[id], maxCells.value)
			return { id, name: components.find(c => c.id === id)?.name ?? id, cells, summary: uptimeSummary(cells) }
		})
})
</script>

<style scoped>
.uptime-cell {
	flex: 1 1 0;
	min-width: 1px;
	border-radius: 1px;
}
.uptime-key {
	display: inline-block;
	width: 8px;
	border-radius: 1px;
}
.cell-none {
	height: 25%;
}
.cell-ok {
	height: 50%;
}
.cell-warn {
	height: 75%;
}
.cell-fail {
	height: 100%;
}
.uptime-key.cell-none {
	height: 4px;
}
.uptime-key.cell-ok {
	height: 8px;
}
.uptime-key.cell-warn {
	height: 11px;
}
.uptime-key.cell-fail {
	height: 14px;
}
</style>
