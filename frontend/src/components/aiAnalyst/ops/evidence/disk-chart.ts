// `disk_forecast`'s chart: the node's used disk per day (its runs' samples), a dashed projection along
// the evidence's slope, and a line at each watermark. The design follows the health charts
// (`health/health-charts.ts`): one axis, one unit (GB), a 2px line with >= 8px markers, recessive
// axes and a hairline grid, the theme's mode-stepped data hue (`useSocChartColors`), and every text in
// the theme's ink. The watermarks are thresholds: the low one neutral, the high one the warning colour
// and the flood stage the error colour, each labelled in words, so none is told apart by colour alone.
//
// The tooltip is HTML (ECharts' default): every value in it is escaped, the node name included, and
// the series' names are fixed words. The axis and mark-line labels are drawn on the canvas, as text.
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, MarkLineComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { DiskForecastView, DiskPoint } from "./evidence"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { formatTime } from "../../health/health"
import { escapeHtml } from "../../usage/usage-chart"
import { bytesText, daysText, gbPerDayText, gbText, GIB, pctText, utcText } from "./evidence"

export type DiskChartOption = ComposeOption<
	LineSeriesOption | GridComponentOption | TooltipComponentOption | MarkLineComponentOption
>

export const NEUTRAL = "#8A8F98"
const DAY_MS = 24 * 60 * 60 * 1000

export interface DiskChartColors {
	primary: string
	warning: string
	error: string
}

export interface DiskChart {
	option: DiskChartOption
	/** The chart's aria-label: what it shows, in words and numbers. */
	summary: string
}

const WATERMARK_COLOR = { low: "neutral", high: "warning", flood_stage: "error" } as const

/** A sample's or projection point's time as local text, for the tooltip. */
function when(ms: number): string {
	return formatTime(new Date(ms).toISOString())
}

/** The tooltip's HTML for one point: every value escaped. */
export function diskTooltip(node: string, kind: "sample" | "projection", ms: number, gb: number, totalGb: number | null): string {
	const pct = totalGb !== null && totalGb > 0 ? ` (${pctText(Math.round((gb / totalGb) * 1000) / 10)})` : ""
	const what = kind === "sample" ? "Used" : "Projected"
	return (
		`<div style="padding:8px 10px">` +
		`<div style="opacity:.8;font-size:11px">${escapeHtml(node)}</div>` +
		`<div style="opacity:.8;font-size:11px" title="${escapeHtml(utcText(ms))}">${escapeHtml(when(ms))}</div>` +
		`<div><span style="opacity:.8">${escapeHtml(what)}</span> <b>${escapeHtml(gbText(gb))}${escapeHtml(pct)}</b></div>` +
		`</div>`
	)
}

/** Where the projection starts: the evidence's used GB at the finding's `last_seen`. */
export interface DiskAnchor {
	t: number
	usedGb: number
}

/**
 * The chart, or null with fewer than two points (the view shows the numbers only). The projection
 * starts at `anchor` (the evidence's `used_gb` at the finding's `last_seen`), else at the newest sample.
 */
export function buildDiskChart(
	view: DiskForecastView,
	points: DiskPoint[],
	horizonDays: number | null,
	colors: DiskChartColors,
	style: Record<string, string>,
	anchor: DiskAnchor | null = null
): DiskChart | null {
	if (points.length < 2) return null
	const muted = style["fg-secondary-color"]
	const hairline = style["border-color"]
	const surface = style["bg-default-color"]
	const font = style["font-family"]
	const axisText = { color: muted, fontFamily: font, fontSize: 11 }
	const last = points[points.length - 1]
	const totalGb = view.totalGb ?? last.total / GIB
	// Each sample carries its own disk total, for its own %.
	const used = points.map(p => [p.t, p.used / GIB, p.total / GIB] as [number, number, number])

	const projection: [number, number, number][] = []
	if (view.slope !== null && horizonDays !== null && horizonDays > 0) {
		const from = anchor ?? { t: last.t, usedGb: last.used / GIB }
		const end = from.t + horizonDays * DAY_MS
		projection.push([from.t, from.usedGb, totalGb], [end, from.usedGb + view.slope * horizonDays, totalGb])
	}

	const lineColor = (key: keyof typeof WATERMARK_COLOR) => {
		const tone = WATERMARK_COLOR[key]
		return tone === "neutral" ? NEUTRAL : colors[tone]
	}
	const marks = view.watermarks.filter(w => w.bytes !== null)
	const markLine: MarkLineComponentOption = {
		silent: true,
		symbol: "none",
		animation: false,
		data: marks.map(w => ({
			name: w.label,
			yAxis: (w.bytes as number) / GIB,
			lineStyle: { color: lineColor(w.key), width: 1, type: "solid" },
			label: {
				formatter: `${w.label} ${pctText(w.pct)}`,
				position: "insideEndTop",
				color: muted,
				fontFamily: font,
				fontSize: 10
			}
		}))
	}

	const values = [...used.map(p => p[1]), ...projection.map(p => p[1]), ...marks.map(w => (w.bytes as number) / GIB)]
	const max = Math.max(totalGb, ...values)

	const series: LineSeriesOption[] = [
		{
			type: "line",
			name: "Used",
			data: used,
			showSymbol: true,
			symbol: "circle",
			symbolSize: 8,
			lineStyle: { width: 2, color: colors.primary, cap: "round", join: "round" },
			itemStyle: { color: colors.primary, borderColor: surface, borderWidth: 2 },
			emphasis: { focus: "none", scale: false },
			markLine,
			z: 3
		}
	]
	if (projection.length) {
		series.push({
			type: "line",
			name: "Projected",
			data: projection,
			showSymbol: false,
			symbol: "circle",
			symbolSize: 8,
			lineStyle: { width: 2, color: colors.primary, type: "dashed", cap: "round" },
			itemStyle: { color: colors.primary, borderColor: surface, borderWidth: 2 },
			emphasis: { focus: "none", scale: false },
			z: 2
		})
	}

	const option: DiskChartOption = {
		animation: false,
		backgroundColor: "transparent",
		grid: { left: 8, right: 16, top: 16, bottom: 4, containLabel: true },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "item" }),
			formatter: (params: unknown) => {
				const p = (Array.isArray(params) ? params[0] : params) as { seriesName?: string; value?: unknown } | undefined
				const value = p?.value
				if (!Array.isArray(value) || typeof value[0] !== "number" || typeof value[1] !== "number") return ""
				const total = typeof value[2] === "number" ? value[2] : null
				return diskTooltip(view.node, p?.seriesName === "Projected" ? "projection" : "sample", value[0], value[1], total)
			}
		},
		xAxis: {
			type: "time",
			axisLine: { lineStyle: { color: hairline, width: 1 } },
			axisTick: { show: false },
			splitLine: { show: false },
			axisLabel: { ...axisText, hideOverlap: true }
		},
		yAxis: {
			type: "value",
			min: 0,
			max: Math.ceil(max * 1.02),
			splitNumber: 3,
			axisLine: { show: false },
			axisTick: { show: false },
			splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" } },
			axisLabel: { ...axisText, formatter: (v: number) => `${Math.round(v).toLocaleString()} GB` }
		},
		series
	}

	const first = points[0]
	const parts = [
		`Used disk on ${view.node}, one sample a day: ${bytesText(first.used)} on ${when(first.t)}, ${bytesText(last.used)} on ${when(last.t)} (${points.length} days).`
	]
	if (projection.length && view.slope !== null) {
		parts.push(`Projected at ${gbPerDayText(view.slope)} for ${daysText(horizonDays)}.`)
	}
	for (const w of marks) parts.push(`${w.label} at ${pctText(w.pct)} (${bytesText(w.bytes)}).`)
	return { option, summary: parts.join(" ") }
}
