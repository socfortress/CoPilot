/**
 * The health dashboard's chart options: a null bucket is a gap, never a zero; a chart with no
 * values at all has no option (the card says "No data"); failures wear the error colour against a
 * neutral grey; cost has no value-axis labels (float-made dollar figures) and its tooltip shows
 * the API's string; the tooltip escapes the bucket time.
 */
import { describe, expect, it } from "vitest"
import { buildHealthCharts, NEUTRAL } from "../health-charts"
import { bucket, must } from "./fixtures"

const STYLE = {
	"fg-secondary-color": "#777",
	"border-color": "#eee",
	"bg-default-color": "#fff",
	"font-family": "sans-serif"
}
const COLORS = { primary: "#A87400", secondary: "#2A78D6", error: "#FF0156" }

interface Option {
	series: { name: string; data: (number | string)[]; itemStyle?: { color: string }; stack?: string; barGap?: string }[]
	yAxis: { axisLabel: { show?: boolean } }
	tooltip: { formatter: (p: unknown) => string }
}

function charts(series = [bucket("2026-10-22T07:00:00Z"), bucket("2026-10-22T08:00:00Z", { investigations_failed: null, cost_usd: null })]) {
	return buildHealthCharts(series, 24, COLORS, STYLE)
}

describe("talon health charts", () => {
	it("five charts in order, with a legend only for two series", () => {
		const list = charts()
		expect(list.map(c => c.id)).toEqual(["investigations", "duration", "queue", "tools", "cost"])
		expect(must(list.find(c => c.id === "queue")).legend).toEqual([])
		expect(must(list.find(c => c.id === "investigations")).legend.map(l => l.name)).toEqual(["Completed", "Failed"])
	})

	it("failures are the error colour, stacked on a neutral whole", () => {
		const option = charts()[0].option as unknown as Option
		expect(option.series.map(s => s.itemStyle?.color)).toEqual([NEUTRAL, COLORS.error])
		expect(option.series.every(s => s.stack === "total")).toBe(true)
		const tools = charts()[3].option as unknown as Option
		expect(tools.series.map(s => s.itemStyle?.color)).toEqual([NEUTRAL, COLORS.error])
		expect(tools.series.every(s => s.barGap === "-100%")).toBe(true)
	})

	it("a series with no data anywhere is a note beside the chart, never zeros", () => {
		const tools = must(charts().find(c => c.id === "tools"))
		expect(tools.notes).toEqual(["Tool errors: no data"])
		expect((tools.option as unknown as Option).series[1].data).toEqual(["-", "-"])
	})

	it("a null bucket is a gap, and the tooltip says no data", () => {
		const option = charts()[0].option as unknown as Option
		expect(option.series[1].data).toEqual([1, "-"])
		const html = option.tooltip.formatter([{ dataIndex: 1 }])
		expect(html).toContain("no data")
		expect(html).not.toMatch(/Failed<\/span>\s*<b[^>]*>0</)
	})

	it("a metric with no data anywhere has no chart", () => {
		const series = [bucket("a", { queue_depth_max: null }), bucket("b", { queue_depth_max: null })]
		expect(must(charts(series).find(c => c.id === "queue")).option).toBeNull()
		expect(must(charts(series).find(c => c.id === "queue")).summary).toContain("no data")
	})

	it("cost: no value-axis labels, the API's string in the tooltip", () => {
		const option = charts()[4].option as unknown as Option
		expect(option.yAxis.axisLabel.show).toBe(false)
		expect(option.tooltip.formatter([{ dataIndex: 0 }])).toContain("$1.2345")
		expect(option.tooltip.formatter([{ dataIndex: 1 }])).toContain("no data")
	})

	it("escapes the bucket time it was sent", () => {
		const option = charts([bucket("<img src=x onerror=alert(1)>")])[0].option as unknown as Option
		const html = option.tooltip.formatter([{ dataIndex: 0 }])
		expect(html).not.toContain("<img")
		expect(html).toContain("&lt;img")
	})
})
