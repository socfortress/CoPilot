/**
 * The account page's failures over time (#1328): its points and its ECharts option, as plain
 * functions (CloudFailuresTrendChart.vue draws them, CloudFailuresTrend.vue lays out the section).
 *
 * One column per completed scan, oldest on the left, its unmuted failures stacked by severity on
 * one axis. Critical sits on the baseline, so the most severe failures compare across scans. Severity
 * is ordinal, so the stack is one red ramp: critical is the end that stands out from the surface,
 * the darkest step on the light one and the lightest on the dark one. Both ramps pass the dataviz
 * palette checks in ordinal mode (light on #FFFFFF, dark on #26282D: one hue, monotone lightness,
 * visible steps, the faint end above 2:1). An unknown severity (one Prowler's metadata didn't name)
 * is a neutral grey on top of the stack.
 *
 * Marks: columns of at most 24px, a 4px rounded top on each column's top segment only, and a 2px
 * gap in the surface colour between segments; the grid and axes are hairline. The tooltip names the
 * scan, its failures by severity, the total and what changed since the scan before. Every string in
 * it is CoPilot's (labels, numbers and dates), never the customer's cloud's, and the date is escaped
 * all the same: ECharts puts the tooltip in the page as HTML.
 */
import type { BarSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { CloudScan, CloudSeverity } from "@/types/cloud-assessment"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { failedBySeverity, SEVERITIES, SEVERITY_LABELS } from "./utils"

export type TrendChartOption = ComposeOption<BarSeriesOption | GridComponentOption | TooltipComponentOption>

/** Per mode, the colour of each severity's segment. */
export const TREND_COLORS: Record<"light" | "dark", Record<CloudSeverity, string>> = {
	light: {
		critical: "#861118",
		high: "#b01e25",
		medium: "#cf4040",
		low: "#de6f68",
		informational: "#ea9891",
		unknown: "#868b94"
	},
	dark: {
		critical: "#fbb7b0",
		high: "#f58b84",
		medium: "#e8605b",
		low: "#cc3d3d",
		informational: "#a5292b",
		unknown: "#7d828b"
	}
}

/** One completed scan, as the chart reads it. */
export interface TrendPoint {
	id: number
	/** When it completed (else started, else was queued), as the API sent it. */
	at: string
	bySeverity: Record<CloudSeverity, number>
	failed: number
	newFailed: number
	resolved: number
	/** The account's first completed scan: nothing to compare with. */
	first: boolean
}

/** The account's completed scans, oldest first. */
export function trendPoints(scans: CloudScan[]): TrendPoint[] {
	return scans
		.filter(scan => scan.status === "completed")
		.sort((a, b) => a.id - b.id)
		.map(scan => ({
			id: scan.id,
			at: scan.completed_at ?? scan.started_at ?? scan.queued_at ?? "",
			bySeverity: failedBySeverity(scan.counts),
			failed: scan.counts.failed,
			newFailed: scan.counts.new_failed,
			resolved: scan.counts.resolved_failed,
			first: scan.previous_scan_id === null
		}))
}

/** The severities drawn, in stack order (bottom first): every named one, and unknown only when a scan has some. */
export function trendSeverities(points: TrendPoint[]): CloudSeverity[] {
	const unknown = points.some(point => point.bySeverity.unknown > 0)
	return SEVERITIES.filter(severity => severity !== "unknown" || unknown)
}

/** What changed since the scan before, in words. */
export function changeText(point: Pick<TrendPoint, "first" | "newFailed" | "resolved">): string {
	return point.first ? "first scan" : `${point.newFailed} new, ${point.resolved} resolved`
}

/** The chart's accessible name: what it shows and where it starts and ends. */
export function trendSummary(points: TrendPoint[], date: (at: string) => string): string {
	const first = points[0]
	const last = points.at(-1)
	if (!first || !last) return "Failures by severity: no completed scans"
	return `Failures by severity across ${points.length} completed scans: ${first.failed} on ${date(first.at)}, ${last.failed} on ${date(last.at)}`
}

function escapeHtml(text: string): string {
	return text
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
}

export function trendTooltipHtml(
	point: TrendPoint,
	options: { colors: Record<CloudSeverity, string>; muted: string; when: (at: string) => string }
): string {
	const rows = SEVERITIES.filter(severity => point.bySeverity[severity] > 0)
		.map(
			severity =>
				`<div style="display:flex;align-items:center;gap:6px;line-height:1.6">` +
				`<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${options.colors[severity]}"></span>` +
				`${SEVERITY_LABELS[severity]}<b style="margin-left:auto;padding-left:16px;font-variant-numeric:tabular-nums">${point.bySeverity[severity].toLocaleString()}</b></div>`
		)
		.join("")
	const total = point.failed
		? `<div style="display:flex;margin-top:4px;padding-top:4px;border-top:1px solid var(--border-color)">Failed<b style="margin-left:auto;padding-left:16px;font-variant-numeric:tabular-nums">${point.failed.toLocaleString()}</b></div>`
		: `<div>No failures</div>`
	return (
		`<div style="font-size:11px;color:${options.muted};padding:6px 10px 4px;background-color:var(--bg-default-color)">` +
		`Scan #${point.id} · ${escapeHtml(options.when(point.at))}</div>` +
		`<div style="padding:4px 10px 8px">${rows}${total}` +
		`<div style="margin-top:2px;color:${options.muted}">${changeText(point)}</div></div>`
	)
}

/**
 * Which column labels show: about `max` of them, evenly spaced, always the selected scan's, and
 * none crowding it.
 */
export function shownLabels(count: number, selected: number, max = 8): Set<number> {
	const step = Math.max(1, Math.ceil(count / max))
	const shown = new Set<number>()
	for (let index = 0; index < count; index += step) {
		if (selected < 0 || index === selected || Math.abs(index - selected) >= step) shown.add(index)
	}
	if (selected >= 0 && selected < count) shown.add(selected)
	return shown
}

export function buildTrendOption(
	points: TrendPoint[],
	options: {
		style: Record<string, string>
		dark: boolean
		selectedId: number | null
		/** A column's label (a short date). */
		label: (at: string) => string
		/** The tooltip's date and time. */
		when: (at: string) => string
	}
): TrendChartOption {
	const { style } = options
	const colors = TREND_COLORS[options.dark ? "dark" : "light"]
	const surface = style["bg-default-color"]
	const muted = style["fg-secondary-color"]
	const ink = style["fg-default-color"]
	const hairline = style["border-color"]
	const font = style["font-family"]
	const severities = trendSeverities(points)
	const selected = points.findIndex(point => point.id === options.selectedId)
	const labels = shownLabels(points.length, selected)
	// Each column's top segment: the last severity, in stack order, with a failure.
	const tops = points.map(point => severities.findLast(severity => point.bySeverity[severity] > 0))

	const series: BarSeriesOption[] = severities.map(severity => ({
		type: "bar",
		name: SEVERITY_LABELS[severity],
		stack: "failed",
		barMaxWidth: 24,
		barCategoryGap: "35%",
		data: points.map((point, index) => ({
			value: point.bySeverity[severity],
			itemStyle: { borderRadius: tops[index] === severity ? [4, 4, 0, 0] : 0 }
		})),
		// The surface-coloured edge is the 2px gap between segments, not an outline.
		itemStyle: { color: colors[severity], borderColor: surface, borderWidth: 1 },
		emphasis: { disabled: true },
		cursor: "pointer"
	}))

	return {
		animation: false,
		grid: { left: 8, right: 16, top: 12, bottom: 4, outerBoundsMode: "same", outerBoundsContain: "axisLabel" },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			// The whole column's slot answers, not only its painted segments.
			// On the page's body: the section around the chart clips what overflows it.
			appendTo: "body",
			// Behind the columns (the bars draw at z 2), so the hovered one keeps its colours.
			axisPointer: { type: "shadow", z: 1, shadowStyle: { color: hairline, opacity: 0.5 } },
			formatter: (params: unknown) => {
				const first = Array.isArray(params) ? params[0] : params
				const point = points[(first as { dataIndex?: number } | undefined)?.dataIndex ?? -1]
				return point ? trendTooltipHtml(point, { colors, muted, when: options.when }) : ""
			}
		},
		xAxis: {
			type: "category",
			data: points.map(point => options.label(point.at)),
			axisLine: { lineStyle: { color: hairline, width: 1 } },
			axisTick: { show: false },
			axisLabel: {
				color: muted,
				fontFamily: font,
				fontSize: 11,
				interval: (index: number) => labels.has(index),
				// The selected scan's date, in the ink of the text around it, on a tint.
				formatter: (value: string, index: number) => (index === selected ? `{selected|${value}}` : value),
				rich: {
					selected: {
						color: ink,
						fontFamily: font,
						fontSize: 11,
						fontWeight: 600,
						backgroundColor: hairline,
						borderRadius: 3,
						padding: [2, 4]
					}
				}
			}
		},
		yAxis: {
			type: "value",
			minInterval: 1,
			splitNumber: 3,
			axisLabel: {
				color: muted,
				fontFamily: font,
				fontSize: 11,
				formatter: (value: number) => value.toLocaleString()
			},
			splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" } }
		},
		series
	}
}
