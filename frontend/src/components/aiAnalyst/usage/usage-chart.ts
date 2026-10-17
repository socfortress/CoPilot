// The Usage tab's chart option, as a plain function (TalonUsageChart.vue renders it).
//
// One series, cost per group, so no legend: the title names it. Days are columns in date order;
// every other grouping is horizontal bars, the costliest at the top, at most `USAGE_CHART_MAX_BARS`
// (the table beside it lists every group). Bars are <= 24px with a 4px rounded data end; grid and
// axes are hairline and recessive; a per-bar tooltip gives the group and its cost **exactly as the
// API's string**. The amounts are parsed with `Number()` only to size the bars, so the value axis
// carries no labels (a tick would be a float-derived dollar figure); its hairline grid stays for
// reading lengths, and the tooltip and the table give the exact amounts. The hue is the SOC charts' amber, stepped per mode
// and validated with the dataviz palette checks (light #A87400 on #FCFCFB, dark #C98500 on
// #26282D: all pass).
//
// The tooltip is HTML (ECharts' default render mode), so every API string in it is escaped.
import type { BarSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { TalonUsageReport } from "@/types/talonUsage"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { formatUsd, usageGroupLabel } from "./usage"

export const USAGE_CHART_COLORS = { light: "#A87400", dark: "#C98500" } as const
export const USAGE_CHART_MAX_BARS = 15

export type UsageChartOption = ComposeOption<BarSeriesOption | GridComponentOption | TooltipComponentOption>

/** For drawing only: a decimal string as a number (0 for anything that isn't one). */
export function costForDrawing(cost: string | null | undefined): number {
	const value = typeof cost === "string" ? Number(cost) : Number.NaN
	return Number.isFinite(value) && value > 0 ? value : 0
}

export function escapeHtml(text: string): string {
	return text
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
}

interface Bar {
	label: string
	/** The API's string, shown in the tooltip as it is. */
	cost: string
	complete: boolean
	/** Parsed, to size the bar. */
	value: number
}

export function usageChartBars(report: TalonUsageReport): Bar[] {
	const bars = report.groups.map(group => ({
		label: usageGroupLabel(group, report.group_by),
		cost: group.cost_usd,
		complete: group.cost_complete,
		value: costForDrawing(group.cost_usd)
	}))
	// Days stay in date order and are all shown; other groupings come costliest first (the API's
	// order) and are cut to the top few.
	return report.group_by === "day" ? bars : bars.slice(0, USAGE_CHART_MAX_BARS)
}

export function usageChartSummary(report: TalonUsageReport): string {
	const bars = usageChartBars(report)
	const by = report.group_by
	if (!bars.length) return `Cost by ${by}: nothing in this range`
	const top = bars.reduce((best, bar) => (bar.value > best.value ? bar : best), bars[0])
	return `Cost by ${by} from ${report.from} to ${report.to}, ${report.groups.length} group(s); highest ${top.label} at ${formatUsd(top.cost)}; total ${formatUsd(report.total.cost_usd)}`
}

export function usageTooltipHtml(bar: Pick<Bar, "label" | "cost" | "complete">): string {
	const incomplete = bar.complete ? "" : `<div style="opacity:.75">incomplete: some responses had no price</div>`
	return `<div style="padding:8px 10px"><div>${escapeHtml(bar.label)}</div><div><b>${escapeHtml(formatUsd(bar.cost))}</b></div>${incomplete}</div>`
}

/** The option, or null when there is nothing to draw. */
export function buildUsageChartOption(
	report: TalonUsageReport,
	style: Record<string, string>,
	dark: boolean
): UsageChartOption | null {
	const bars = usageChartBars(report)
	if (!bars.length) return null
	const color = USAGE_CHART_COLORS[dark ? "dark" : "light"]
	const muted = style["fg-secondary-color"]
	const hairline = style["border-color"]
	const font = style["font-family"]
	const columns = report.group_by === "day"
	// Horizontal bars read top-down, but a category y axis runs bottom-up: reverse so the first
	// (costliest) group is at the top.
	const ordered = columns ? bars : [...bars].reverse()

	const categoryAxis = {
		type: "category" as const,
		data: ordered.map(bar => bar.label),
		axisLine: { lineStyle: { color: hairline, width: 1 } },
		axisTick: { show: false },
		axisLabel: { color: muted, fontFamily: font, fontSize: 11, width: 160, overflow: "truncate" as const }
	}
	const valueAxis = {
		type: "value" as const,
		axisLine: { show: false },
		axisTick: { show: false },
		splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" as const } },
		// No tick labels: they would be figures made from parsed floats (the tooltip and table have the strings).
		axisLabel: { show: false }
	}

	return {
		animation: false,
		grid: { left: 8, right: 24, top: 16, bottom: 8, containLabel: true },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "item" }),
			formatter: (params: unknown) => {
				const index = (params as { dataIndex?: number }).dataIndex ?? -1
				const bar = ordered[index]
				return bar ? usageTooltipHtml(bar) : ""
			}
		},
		xAxis: columns ? categoryAxis : valueAxis,
		yAxis: columns ? valueAxis : categoryAxis,
		series: [
			{
				type: "bar",
				name: "Cost (USD)",
				data: ordered.map(bar => bar.value),
				barMaxWidth: 24,
				itemStyle: { color, borderRadius: columns ? [4, 4, 0, 0] : [0, 4, 4, 0] },
				emphasis: { focus: "none" }
			}
		]
	}
}
