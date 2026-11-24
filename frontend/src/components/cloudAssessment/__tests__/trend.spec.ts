/**
 * The failures-over-time chart's points and option (#1328): completed scans only, oldest first;
 * one stack of severities with critical on the baseline and a rounded top on each column's top
 * segment only; the selected scan's date always labelled; a tooltip that says what changed.
 */
import type { BarSeriesOption } from "echarts/charts"
import type { TrendPoint } from "../trend"
import { describe, expect, it } from "vitest"
import {
	buildTrendOption,
	changeText,
	shownLabels,
	TREND_COLORS,
	trendPoints,
	trendSeverities,
	trendSummary,
	trendTooltipHtml
} from "../trend"
import { counts, scan } from "./fixtures"

const STYLE = {
	"bg-default-color": "#ffffff",
	"fg-secondary-color": "#495465",
	"fg-default-color": "#000000",
	"border-color": "#e2e6e9",
	"font-family": "Public Sans",
	"primary-color": "#ffb600"
}

const scans = [
	scan(12, { status: "running", completed_at: null, counts: counts() }),
	scan(11, { counts: counts({ failed: 5, failed_critical: 1, failed_high: 4, new_failed: 2, resolved_failed: 3 }) }),
	scan(9, { status: "failed", counts: counts() }),
	scan(10, { counts: counts({ failed: 6, failed_high: 2, failed_low: 4 }), previous_scan_id: 8 }),
	scan(8, { counts: counts({ failed: 1, failed_unknown: 1 }), previous_scan_id: null })
]

function option(selectedId: number | null = 11, dark = false) {
	const points = trendPoints(scans)
	return buildTrendOption(points, { style: STYLE, dark, selectedId, label: at => at.slice(5, 10), when: at => at })
}

function seriesOf(selectedId: number | null = 11) {
	return option(selectedId).series as BarSeriesOption[]
}

describe("the points", () => {
	it("are the completed scans, oldest first", () => {
		const points = trendPoints(scans)
		expect(points.map(point => point.id)).toEqual([8, 10, 11])
		expect(points[2]).toMatchObject({
			failed: 5,
			newFailed: 2,
			resolved: 3,
			first: false,
			at: "2026-11-20T10:20:00"
		})
		expect(points[0]?.first).toBe(true)
		expect(points[1]?.bySeverity).toMatchObject({ critical: 0, high: 2, low: 4 })
	})

	it("draw every named severity, and unknown only when a scan has some", () => {
		expect(trendSeverities(trendPoints(scans))).toEqual([
			"critical",
			"high",
			"medium",
			"low",
			"informational",
			"unknown"
		])
		expect(trendSeverities(trendPoints(scans.slice(0, 2)))).toEqual([
			"critical",
			"high",
			"medium",
			"low",
			"informational"
		])
	})
})

describe("the option", () => {
	it("stacks the severities on one axis, critical on the baseline, in the ramp of the mode", () => {
		const series = seriesOf()
		expect(series.map(item => item.name)).toEqual(["Critical", "High", "Medium", "Low", "Informational", "Unknown"])
		expect(new Set(series.map(item => item.stack))).toEqual(new Set(["failed"]))
		expect(series.every(item => item.barMaxWidth === 24)).toBe(true)
		expect(series[0]?.itemStyle?.color).toBe(TREND_COLORS.light.critical)
		const dark = buildTrendOption(trendPoints(scans), {
			style: STYLE,
			dark: true,
			selectedId: null,
			label: at => at,
			when: at => at
		}).series as BarSeriesOption[]
		expect(dark[0]?.itemStyle?.color).toBe(TREND_COLORS.dark.critical)
		expect(Array.isArray(option().yAxis)).toBe(false)
	})

	it("parts the segments with the surface colour and rounds only each column's top one", () => {
		const series = seriesOf()
		expect(
			series.every(item => item.itemStyle?.borderColor === "#ffffff" && item.itemStyle?.borderWidth === 1)
		).toBe(true)
		const radius = (name: string, index: number) => {
			const data = series.find(item => item.name === name)?.data as { itemStyle: { borderRadius: unknown } }[]
			return data[index]?.itemStyle.borderRadius
		}
		// scan 8: only unknown; scan 10: high and low, low on top; scan 11: critical and high
		expect(radius("Unknown", 0)).toEqual([4, 4, 0, 0])
		expect(radius("Low", 1)).toEqual([4, 4, 0, 0])
		expect(radius("High", 1)).toBe(0)
		expect(radius("High", 2)).toEqual([4, 4, 0, 0])
		expect(radius("Critical", 2)).toBe(0)
	})

	it("labels the selected scan's column, set apart", () => {
		const axis = option(10).xAxis as {
			data: string[]
			axisLabel: { formatter: (value: string, index: number) => string; interval: (index: number) => boolean }
		}
		expect(axis.data).toEqual(["11-20", "11-20", "11-20"])
		expect(axis.axisLabel.formatter("11-20", 1)).toBe("{selected|11-20}")
		expect(axis.axisLabel.formatter("11-20", 0)).toBe("11-20")
		expect([0, 1, 2].every(index => axis.axisLabel.interval(index))).toBe(true)
	})

	it("answers anywhere in a column's slot, with the scan, its severities and what changed", () => {
		const tooltip = option().tooltip as {
			trigger: string
			appendTo: string
			axisPointer: { type: string; z: number }
			formatter: (params: unknown) => string
		}
		expect(tooltip.trigger).toBe("axis")
		expect(tooltip.axisPointer).toMatchObject({ type: "shadow", z: 1 }) // behind the columns
		expect(tooltip.appendTo).toBe("body") // the section around the chart clips
		const html = tooltip.formatter([{ dataIndex: 2 }])
		expect(html).toContain("Scan #11")
		expect(html).toContain("Critical")
		expect(html).toContain("High")
		expect(html).not.toContain("Medium")
		expect(html).toContain("2 new, 3 resolved")
	})
})

/** The point at `index`, failing the test when there is none. */
function pointAt(points: TrendPoint[], index: number): TrendPoint {
	const point = points.at(index)
	if (!point) throw new Error(`no point at ${index}`)
	return point
}

describe("the words", () => {
	it("say what changed, or that there was nothing to compare with", () => {
		const points = trendPoints(scans)
		expect(changeText(pointAt(points, 0))).toBe("first scan")
		expect(changeText(pointAt(points, -1))).toBe("2 new, 3 resolved")
	})

	it("sum the chart up for a screen reader", () => {
		expect(trendSummary(trendPoints(scans), at => at.slice(0, 10))).toBe(
			"Failures by severity across 3 completed scans: 1 on 2026-11-20, 5 on 2026-11-20"
		)
		expect(trendSummary([], at => at)).toBe("Failures by severity: no completed scans")
	})

	it("say a scan without failures has none", () => {
		const point = pointAt(trendPoints([scan(3, { counts: counts() })]), 0)
		const html = trendTooltipHtml(point, { colors: TREND_COLORS.light, muted: "#495465", when: () => "today" })
		expect(html).toContain("No failures")
		expect(html).toContain("Scan #3 · today")
	})

	it("escape the date, which the tooltip puts in the page as HTML", () => {
		const point = pointAt(trendPoints([scan(3)]), 0)
		const html = trendTooltipHtml(point, {
			colors: TREND_COLORS.light,
			muted: "#495465",
			when: () => `<img src=x onerror="alert(1)">`
		})
		expect(html).not.toContain("<img")
		expect(html).toContain("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;")
	})
})

describe("the column labels", () => {
	it("all show while they fit", () => {
		expect([...shownLabels(5, 2)]).toEqual([0, 1, 2, 3, 4])
	})

	it("thin out past eight, keeping the selected one clear of its neighbours", () => {
		const shown = shownLabels(30, 13)
		expect(shown.has(13)).toBe(true)
		expect(shown.has(12)).toBe(false) // a step of 4: 12 and 16 are too close to 13
		expect(shown.has(16)).toBe(false)
		expect(shown.has(8) && shown.has(20)).toBe(true)
		expect(shown.size).toBeLessThanOrEqual(8)
		expect([...shownLabels(30, -1)]).toEqual([0, 4, 8, 12, 16, 20, 24, 28])
	})
})
