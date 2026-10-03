<template>
	<n-empty v-if="!rows.length" :description="emptyText" class="py-4" />
	<VChart
		v-else
		class="load-bars w-full"
		autoresize
		:option
		:style="{ height: `${chartHeight}px`, width: '100%' }"
		role="img"
		:aria-label
		data-testid="load-bars"
	/>
</template>

<script setup lang="ts">
// Open load as horizontal stacked bars (alerts | cases) on one shared scale, with each
// row's total and its at-risk / past-SLA counts printed beside it — never left to colour
// alone. Bars cap at 12px thick, with a 2px surface gap between the two segments; a row
// label can carry a coloured dot (a severity).
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
import { useResolvedColors, useSocChartColors } from "../charts/chart-colors"

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
const chartHeight = computed(() => LEGEND_HEIGHT + rows.length * ROW_HEIGHT + 4)
const scale = computed(() => Math.max(1, ...rows.map(row => row.alerts + row.cases)))
const ariaLabel = computed(() =>
	rows.map(row => `${row.label}: ${row.alerts} alerts, ${row.cases} cases, ${row.at_risk} at risk, ${row.breached} past SLA`).join("; ")
)

/** A row's dot, an empty slot when this row has none (so names line up), or nothing without dots. */
function dotSlot(index: number) {
	if (!labelDot) return ""
	return labelDot(rows[index]) ? `{dot${index}|●}` : "{nodot|}"
}

/** The counts beside a bar: the total, then at risk and past SLA, coloured only when non-zero. */
function countsLabel(row: LoadRow, index: number) {
	return `{total|${row.alerts + row.cases}}  {risk${index}|◷ ${row.at_risk}}  {bad${index}|▲ ${row.breached}}`
}

const option = computed(
	(): ComposeOption<BarSeriesOption | GridComponentOption | LegendComponentOption | TooltipComponentOption> => {
		const style = colors.style.value
		const muted = style["fg-secondary-color"]
		const quiet = style["fg-tertiary-color"] ?? muted
		const ink = style["fg-default-color"]
		const font = style["font-family"]
		const surface = style["bg-default-color"]
		const labels = rows.map(row => row.label)

		const leftRich: Record<string, object> = {
			name: { color: ink, fontFamily: font, fontSize: 13, width: LABEL_WIDTH - DOT_WIDTH, overflow: "truncate" },
			nodot: { width: DOT_WIDTH }
		}
		const rightRich: Record<string, object> = {
			total: { color: ink, fontFamily: "monospace", fontSize: 13, width: 36, align: "right" }
		}
		rows.forEach((row, i) => {
			const dot = labelDot?.(row)
			if (dot) leftRich[`dot${i}`] = { color: dot, fontSize: 11, width: DOT_WIDTH }
			rightRich[`risk${i}`] = { color: row.at_risk ? colors.tone("warn") : quiet, fontFamily: "monospace", fontSize: 11 }
			rightRich[`bad${i}`] = { color: row.breached ? colors.tone("bad") : quiet, fontFamily: "monospace", fontSize: 11 }
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
				},
				{
					type: "category",
					inverse: true,
					position: "right",
					data: labels,
					axisLine: { show: false },
					axisTick: { show: false },
					axisLabel: {
						formatter: (_value: string, index: number) => countsLabel(rows[index], index),
						rich: rightRich
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
