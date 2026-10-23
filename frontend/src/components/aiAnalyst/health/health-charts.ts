// The Talon health dashboard's chart options, as plain functions (TalonHealthCharts.vue renders them).
//
// Design (the dataviz method; hues validated with its palette checks):
// - One axis per chart, one unit per axis. Thin marks: columns <= 24px with a 4px rounded data end,
//   2px lines, hairline solid grid, recessive axis text. A legend (HTML, above the chart) for two
//   series; none for one, the title names it. An axis tooltip lists every series at the bucket.
// - Colour by job. Completed vs failed investigations and tool calls vs tool errors mean good/bad,
//   so the failure wears the theme's error colour against a neutral grey for the whole (#8A8F98:
//   CVD dE 10.3 deutan vs #FF0156, contrast >= 3:1 on white and on #26282D); never green against
//   red, which fails deutan (dE 5.7). Duration p50/p95 are identity: the SOC charts' validated
//   amber and blue (light #A87400/#2A78D6, dark #C98500/#3987E5: every check passes). Queue depth
//   and cost are one series in amber.
// - A null bucket is a gap ("no data" in the tooltip and the table), never a zero.
// - Cost is drawn from parsed decimal strings, so its value axis has no tick labels (they would be
//   float-made dollar figures); the tooltip and the table show the API's strings.
// - The tooltip is HTML: the bucket time (an API string) is escaped.
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { TalonMetricsBucket } from "@/types/talonHealth"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { escapeHtml } from "../usage/usage-chart"
import { costValue, formatCount, formatSeconds, formatTime, formatUsdText, hasAny, metricValues, NO_DATA } from "./health"

export const NEUTRAL = "#8A8F98"

export type HealthChartOption = ComposeOption<BarSeriesOption | LineSeriesOption | GridComponentOption | TooltipComponentOption>

export interface ChartColors {
	primary: string
	secondary: string
	error: string
}

interface Series {
	name: string
	kind: "bar" | "line"
	color: string
	values: (number | null)[]
	/** The tooltip's text for bucket i (defaults to the count). */
	text?: (i: number) => string
	stack?: boolean
	/** Drawn over the series before it, same width (errors inside calls). */
	overlap?: boolean
	/** Has the rounded data end (the top of a stack). */
	cap?: boolean
}

export interface HealthChart {
	id: string
	title: string
	/** For the chart's aria-label: what it shows, in words. */
	summary: string
	legend: { name: string; color: string; kind: "bar" | "line" }[]
	/** One line per series with no data at all in the window, e.g. "Errors: no data". */
	notes: string[]
	option: HealthChartOption | null
}

function bucketLabels(series: TalonMetricsBucket[], hours: number) {
	return series.map(b => formatTime(b.t, hours > 24))
}

function buildOption(labels: string[], list: Series[], style: Record<string, string>, valueLabels = true): HealthChartOption {
	const muted = style["fg-secondary-color"]
	const hairline = style["border-color"]
	const surface = style["bg-default-color"]
	const font = style["font-family"]
	const axisText = { color: muted, fontFamily: font, fontSize: 11 }
	const hasBars = list.some(s => s.kind === "bar")
	// ECharts reads barGap across the category's bars: set on every bar when one overlaps.
	const overlap = list.some(s => s.overlap)

	const series = list.map((s): BarSeriesOption | LineSeriesOption => {
		if (s.kind === "line") {
			return {
				type: "line",
				name: s.name,
				data: s.values.map(v => (v === null ? "-" : v)),
				connectNulls: false,
				showSymbol: false,
				symbol: "circle",
				symbolSize: 8,
				lineStyle: { width: 2, color: s.color, cap: "round", join: "round" },
				itemStyle: { color: s.color, borderColor: surface, borderWidth: 2 },
				emphasis: { focus: "none", scale: false }
			}
		}
		return {
			type: "bar",
			name: s.name,
			data: s.values.map(v => (v === null ? "-" : v)),
			stack: s.stack ? "total" : undefined,
			barMaxWidth: 24,
			barGap: overlap ? "-100%" : undefined,
			itemStyle: {
				color: s.color,
				// The 2px surface gap between stacked segments and touching columns.
				borderColor: surface,
				borderWidth: s.stack ? 1 : 0,
				borderRadius: s.cap || !s.stack ? [4, 4, 0, 0] : 0
			},
			emphasis: { focus: "none" }
		}
	})

	return {
		animation: false,
		backgroundColor: "transparent",
		grid: { left: 8, right: 16, top: 12, bottom: 4, containLabel: true },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: hasBars
				? { type: "shadow", shadowStyle: { color: hairline, opacity: 0.35 } }
				: { type: "line", lineStyle: { color: muted, width: 1 } },
			formatter: (params: unknown) => {
				const rows = Array.isArray(params) ? params : [params]
				const index = (rows[0] as { dataIndex?: number })?.dataIndex ?? 0
				const lines = list
					.map(
						s => `<div style="display:flex;align-items:center;gap:6px;margin-top:2px">
							<span style="display:inline-block;width:12px;height:2px;border-radius:1px;background:${s.color}"></span>
							<span style="opacity:.8">${escapeHtml(s.name)}</span>
							<b style="margin-left:auto;padding-left:12px;font-variant-numeric:tabular-nums">${escapeHtml(
								s.values[index] === null ? NO_DATA : s.text ? s.text(index) : formatCount(s.values[index])
							)}</b>
						</div>`
					)
					.join("")
				return `<div style="padding:8px 10px"><div style="color:${muted};font-size:11px">${escapeHtml(labels[index] ?? "")}</div>${lines}</div>`
			}
		},
		xAxis: {
			type: "category",
			data: labels,
			boundaryGap: hasBars,
			axisLine: { lineStyle: { color: hairline, width: 1 } },
			axisTick: { show: false },
			axisLabel: { ...axisText, hideOverlap: true }
		},
		yAxis: {
			type: "value",
			splitNumber: 3,
			minInterval: valueLabels ? 1 : undefined,
			axisLine: { show: false },
			axisTick: { show: false },
			splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" } },
			axisLabel: valueLabels ? { ...axisText, formatter: (v: number) => v.toLocaleString() } : { show: false }
		},
		series
	}
}

function chart(id: string, title: string, summary: string, list: Series[], labels: string[], style: Record<string, string>, valueLabels = true): HealthChart {
	const drawable = list.some(s => hasAny(s.values))
	return {
		id,
		title,
		summary,
		legend: list.length > 1 ? list.map(s => ({ name: s.name, color: s.color, kind: s.kind })) : [],
		notes: drawable ? list.filter(s => !hasAny(s.values)).map(s => `${s.name}: ${NO_DATA}`) : [],
		option: drawable ? buildOption(labels, list, style, valueLabels) : null
	}
}

function total(values: (number | null)[]): number | null {
	return hasAny(values) ? values.reduce<number>((t, v) => t + (v ?? 0), 0) : null
}

function summaryOf(name: string, values: (number | null)[]) {
	const sum = total(values)
	return sum === null ? `${name}: ${NO_DATA}` : `${name}: ${sum.toLocaleString()}`
}

function peak(values: (number | null)[]): number | null {
	return hasAny(values) ? Math.max(...values.filter((v): v is number => v !== null)) : null
}

/** Every chart of the dashboard, in order. A chart whose every value is null has no option. */
export function buildHealthCharts(
	series: TalonMetricsBucket[],
	hours: number,
	colors: ChartColors,
	style: Record<string, string>
): HealthChart[] {
	const labels = bucketLabels(series, hours)
	const completed = metricValues(series, "investigations_completed")
	const failed = metricValues(series, "investigations_failed")
	const p50 = metricValues(series, "duration_p50_s")
	const p95 = metricValues(series, "duration_p95_s")
	const queue = metricValues(series, "queue_depth_max")
	const calls = metricValues(series, "tool_calls")
	const errors = metricValues(series, "tool_errors")
	const cost = series.map(b => costValue(b.cost_usd))
	const window = hours > 24 ? "7 days" : `${hours} h`
	const peakQueue = peak(queue)
	const peakP95 = peak(p95)

	return [
		chart(
			"investigations",
			"Investigations",
			`Investigations per bucket over ${window}. ${summaryOf("Completed", completed)}; ${summaryOf("Failed", failed)}`,
			[
				{ name: "Completed", kind: "bar", color: NEUTRAL, values: completed, stack: true },
				{ name: "Failed", kind: "bar", color: colors.error, values: failed, stack: true, cap: true }
			],
			labels,
			style
		),
		chart(
			"duration",
			"Investigation duration",
			`Investigation duration p50 and p95 over ${window}; highest p95 ${peakP95 === null ? NO_DATA : formatSeconds(peakP95)}`,
			[
				{ name: "p50", kind: "line", color: colors.primary, values: p50, text: i => formatSeconds(p50[i]) },
				{ name: "p95", kind: "line", color: colors.secondary, values: p95, text: i => formatSeconds(p95[i]) }
			],
			labels,
			style
		),
		chart(
			"queue",
			"Queued jobs (max)",
			`Most jobs queued at once per bucket over ${window}; peak ${peakQueue === null ? NO_DATA : peakQueue.toLocaleString()}`,
			[{ name: "Queued jobs", kind: "bar", color: colors.primary, values: queue }],
			labels,
			style
		),
		chart(
			"tools",
			"Tool errors against calls",
			`Investigations' tool calls and tool errors per bucket over ${window}. ${summaryOf("Calls", calls)}; ${summaryOf("Errors", errors)}`,
			[
				{ name: "Tool calls (investigations)", kind: "bar", color: NEUTRAL, values: calls },
				{ name: "Tool errors", kind: "bar", color: colors.error, values: errors, overlap: true }
			],
			labels,
			style
		),
		chart(
			"cost",
			"Cost (USD)",
			`Talon's cost per bucket over ${window}; the exact amounts are in the table`,
			[{ name: "Cost", kind: "bar", color: colors.primary, values: cost, text: i => formatUsdText(series[i]?.cost_usd) }],
			labels,
			style,
			false
		)
	]
}
