<template>
	<n-empty v-if="!rows.length" :description="emptyText" class="py-4" />
	<div v-else class="load-bars flex w-full items-start gap-4">
		<VChart
			class="min-w-0 flex-1"
			autoresize
			:option
			:style="{ height: `${chartHeight}px` }"
			role="img"
			:aria-label
			data-testid="load-bars"
		/>
		<!-- The counts, one line per bar: HTML rather than canvas text, so they keep the page's
		type, line up in fixed columns and carry an icon beside every status colour. -->
		<div class="counts grid shrink-0 gap-x-2" :style="{ gridTemplateRows: `${LEGEND_HEIGHT}px`, gridAutoRows: `${ROW_HEIGHT}px` }" data-testid="load-bars-counts">
			<div class="col-head">Open</div>
			<div class="col-head">At risk</div>
			<div class="col-head">Past SLA</div>
			<template v-for="row in rows" :key="row.key">
				<span class="total" data-testid="load-bars-total">{{ formatCount(row.alerts + row.cases) }}</span>
				<span
					v-for="chip in chipsOf(row)"
					:key="chip.key"
					class="chip"
					:class="{ 'chip--on': chip.value > 0 }"
					:style="{ '--chip-color': chip.color }"
					:aria-label="`${row.label}: ${chip.value} ${chip.label}`"
					:data-testid="`load-bars-${chip.key}`"
				>
					<Icon :name="chip.icon" :size="12" />
					{{ formatCount(chip.value) }}
				</span>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
// Open load as horizontal stacked bars (alerts | cases) on one shared scale, with each
// row's total and its at-risk / past-SLA counts in a column beside it — icon + number
// under a named header, never colour alone. Bars cap at 12px thick, with a 2px surface
// gap between the two segments; a row label can carry a coloured dot (a severity). The
// chart's plot is exactly one ROW_HEIGHT per row below the legend, which is what keeps
// the HTML counts level with their bars.
import type { BarSeriesOption } from "echarts/charts"
import type { GridComponentOption, LegendComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { BarChart } from "echarts/charts"
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import VChart from "vue-echarts"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import Icon from "@/components/common/Icon.vue"
import { useResolvedColors, useSocChartColors } from "../charts/chart-colors"
import { formatCount, SLA_STATE_META, TONE_COLOR } from "../utils"

export interface LoadRow {
	key: string
	label: string
	alerts: number
	cases: number
	at_risk: number
	breached: number
}

const {
	rows,
	emptyText = "Nothing open",
	labelDot
} = defineProps<{
	rows: LoadRow[]
	emptyText?: string
	/** A resolved colour for a dot before the row's label (e.g. its severity), or nothing. */
	labelDot?: (row: LoadRow) => string | undefined
}>()

use([CanvasRenderer, BarChart, GridComponent, LegendComponent, TooltipComponent])

const { primary, secondary } = useSocChartColors()
const colors = useResolvedColors()

const ROW_HEIGHT = 30
/** The label column: a dot slot, then the name, truncated to fit. */
const LABEL_WIDTH = 150
const DOT_WIDTH = 14
const LEGEND_HEIGHT = 28
const chartHeight = computed(() => LEGEND_HEIGHT + rows.length * ROW_HEIGHT)
const scale = computed(() => Math.max(1, ...rows.map(row => row.alerts + row.cases)))
const ariaLabel = computed(() =>
	rows.map(row => `${row.label}: ${row.alerts} alerts, ${row.cases} cases, ${row.at_risk} at risk, ${row.breached} past SLA`).join("; ")
)

/** A row's dot, an empty slot when this row has none (so names line up), or nothing without dots. */
function dotSlot(index: number) {
	if (!labelDot) return ""
	return labelDot(rows[index]) ? `{dot${index}|●}` : "{nodot|}"
}

/** A row's at-risk and past-SLA counts, as the chips beside its bar. */
function chipsOf(row: LoadRow) {
	return [
		{ key: "at-risk", label: "at risk", value: row.at_risk, icon: SLA_STATE_META.at_risk.icon, color: TONE_COLOR.warn },
		{ key: "past-sla", label: "past SLA", value: row.breached, icon: SLA_STATE_META.breached.icon, color: TONE_COLOR.bad }
	]
}

const option = computed(
	(): ComposeOption<BarSeriesOption | GridComponentOption | LegendComponentOption | TooltipComponentOption> => {
		const style = colors.style.value
		const muted = style["fg-secondary-color"]
		const ink = style["fg-default-color"]
		const font = style["font-family"]
		const surface = style["bg-default-color"]
		const labels = rows.map(row => row.label)

		const leftRich: Record<string, object> = {
			name: { color: ink, fontFamily: font, fontSize: 13, width: LABEL_WIDTH - DOT_WIDTH, overflow: "truncate" },
			nodot: { width: DOT_WIDTH }
		}
		rows.forEach((row, i) => {
			const dot = labelDot?.(row)
			if (dot) leftRich[`dot${i}`] = { color: dot, fontSize: 11, width: DOT_WIDTH }
		})

		const segment = (name: string, color: string, values: number[]) => ({
			type: "bar" as const,
			name,
			stack: "load",
			barMaxWidth: 12,
			itemStyle: { color, borderColor: surface, borderWidth: 1, borderRadius: 2 },
			emphasis: { focus: "series" as const },
			data: values
		})

		return {
			backgroundColor: "transparent",
			legend: {
				top: 0,
				left: 0,
				icon: "roundRect",
				itemWidth: 10,
				itemHeight: 10,
				textStyle: { color: muted, fontFamily: font, fontSize: 12 },
				data: ["Alerts", "Cases"]
			},
			grid: {
				left: 0,
				right: 0,
				top: LEGEND_HEIGHT,
				bottom: 0,
				outerBoundsMode: "same",
				outerBoundsContain: "axisLabel"
			},
			tooltip: {
				...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
				axisPointer: { type: "shadow" },
				formatter: params => {
					const index = (Array.isArray(params) ? params[0] : params)?.dataIndex ?? 0
					const row = rows[index]
					if (!row) return ""
					return `<div style="padding:8px 10px;font-family:monospace;font-size:12px"><div>${row.label}</div>
						<div style="color:${muted}">${row.alerts} alerts · ${row.cases} cases</div>
						<div style="color:${muted}">${row.at_risk} at risk · ${row.breached} past SLA</div></div>`
				}
			},
			xAxis: { type: "value", show: false, max: scale.value },
			yAxis: [
				{
					type: "category",
					inverse: true,
					data: labels,
					axisLine: { show: false },
					axisTick: { show: false },
					axisLabel: {
						// Left-aligned in a fixed column, the dot right before the name.
						align: "left",
						margin: LABEL_WIDTH + 8,
						formatter: (value: string, index: number) =>
							`${dotSlot(index)}{name|${value}}`,
						rich: leftRich
					}
				}
			],
			series: [
				segment(
					"Alerts",
					primary.value,
					rows.map(row => row.alerts)
				),
				segment(
					"Cases",
					secondary.value,
					rows.map(row => row.cases)
				)
			]
		}
	}
)
</script>

<style scoped>
.counts {
	grid-template-columns: 2.75rem 4.25rem 4.75rem;
}

.col-head {
	display: flex;
	align-items: flex-start;
	justify-content: flex-end;
	padding-top: 4px;
	font-family: var(--font-family-mono);
	font-size: 10px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	white-space: nowrap;
	color: var(--fg-tertiary-color);
}

.total {
	align-self: center;
	justify-self: end;
	font-family: var(--font-family-mono);
	font-size: 14px;
	font-weight: 600;
	font-variant-numeric: tabular-nums;
	color: var(--fg-default-color);
}

.chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	align-self: center;
	justify-self: end;
	height: 20px;
	padding: 0 6px;
	border-radius: 6px;
	font-family: var(--font-family-mono);
	font-size: 12px;
	font-variant-numeric: tabular-nums;
	color: var(--fg-tertiary-color);
	opacity: 0.55;
}

.chip--on {
	/* Pulled toward the text colour, so a status hue stays readable on its own tint in both modes. */
	color: color-mix(in srgb, var(--chip-color) 72%, var(--fg-default-color));
	background: color-mix(in srgb, var(--chip-color) 14%, transparent);
	box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--chip-color) 28%, transparent);
	opacity: 1;
}
</style>
