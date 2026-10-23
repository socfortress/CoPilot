/**
 * The cost views' pure parts: the date range, group names, the chart's option (built from parsed
 * amounts for drawing only, the tooltip from the API's strings, escaped), the run timeline's layout,
 * and the budget form's rules (CoPilot's `USD_AMOUNT` and `MAX_BUDGET_USD`, as text).
 */
import type { TalonTimelineSpan, TalonUsageFigures, TalonUsageReport } from "@/types/talonUsage"
import { describe, expect, it } from "vitest"
import {
	budgetAmountProblem,
	budgetPayload,
	describeWindow,
	limitText,
	warnAtPercent,
	windowFormFromEntry
} from "../budgets"
import { layoutTimeline, spanSubject, spanTokens, TIMELINE_MIN_WIDTH_PCT, timeMs } from "../run-timeline"
import { compareStages, defaultUsageRange, formatDurationMs, usageGroupLabel, usageRangeProblem } from "../usage"
import {
	buildUsageChartOption,
	costForDrawing,
	USAGE_CHART_MAX_BARS,
	usageChartSummary,
	usageTooltipHtml
} from "../usage-chart"

function figures(cost: string, extra: Partial<TalonUsageFigures> = {}): TalonUsageFigures {
	return {
		responses: 1,
		input_tokens: 10,
		output_tokens: 5,
		cache_read_tokens: 0,
		cache_write_tokens: 0,
		cost_usd: cost,
		unpriced_responses: 0,
		cost_complete: true,
		failed_attempts: 0,
		...extra
	}
}

function report(groups: TalonUsageReport["groups"], extra: Partial<TalonUsageReport> = {}): TalonUsageReport {
	return {
		from: "2026-09-17",
		to: "2026-10-16",
		group_by: "customer",
		customer_code: null,
		groups,
		truncated: false,
		total: figures("0.3"),
		...extra
	}
}

const STYLE = {
	"fg-secondary-color": "#666",
	"border-color": "#eee",
	"font-family": "Inter",
	"fg-default-color": "#111"
}

interface ValueAxisLike {
	type: string
	axisLabel?: { show?: boolean; formatter?: unknown }
}

function chartOption(input: TalonUsageReport, dark: boolean) {
	const option = buildUsageChartOption(input, STYLE, dark)
	if (!option) throw new Error("no option")
	return option
}

describe("the usage range", () => {
	it("opens on the last 30 UTC days, today included", () => {
		expect(defaultUsageRange(new Date("2026-10-16T23:30:00Z"))).toEqual(["2026-09-17", "2026-10-16"])
		expect(usageRangeProblem(...defaultUsageRange())).toBeNull()
	})

	it("at most 366 days, both ends included; never reversed; only real days", () => {
		expect(usageRangeProblem("2025-10-15", "2026-10-16")).toBe("At most 366 days.")
		expect(usageRangeProblem("2025-10-16", "2026-10-16")).toBeNull()
		expect(usageRangeProblem("2026-10-16", "2026-10-15")).toBe("The first day is after the last.")
		expect(usageRangeProblem("2026-02-30", "2026-03-01")).toBe("Pick a first and a last day.")
		expect(usageRangeProblem(null, "2026-03-01")).toBe("Pick a first and a last day.")
	})
})

describe("group names", () => {
	it("say what a null key is under each grouping, and an admin's username", () => {
		expect(usageGroupLabel({ key: null }, "customer")).toBe("No customer (general chat)")
		expect(usageGroupLabel({ key: "ACME" }, "customer")).toBe("ACME")
		expect(usageGroupLabel({ key: null }, "user")).toBe("Investigations (no user)")
		expect(usageGroupLabel({ key: "7", username: "ana" }, "user")).toBe("ana (7)")
		expect(usageGroupLabel({ key: "7" }, "user")).toBe("User 7")
		expect(usageGroupLabel({ key: null }, "model")).toBe("None")
	})

	it("stages in pipeline order and durations for reading", () => {
		expect(["S10", "chat", "S5-escalation", "S2", "S5"].sort(compareStages)).toEqual([
			"S2",
			"S5",
			"S5-escalation",
			"S10",
			"chat"
		])
		expect(formatDurationMs(850)).toBe("850 ms")
		expect(formatDurationMs(12_400)).toBe("12.4 s")
		expect(formatDurationMs(185_000)).toBe("3 min 05 s")
	})
})

describe("the usage chart", () => {
	it("parses amounts for drawing only; anything that isn't one draws as 0", () => {
		expect(costForDrawing("0.000123")).toBe(0.000123)
		expect(costForDrawing("not a number")).toBe(0)
		expect(costForDrawing("-1")).toBe(0)
	})

	it("horizontal bars, the costliest on top, cut to the top few", () => {
		const groups = Array.from({ length: 20 }, (_, i) => ({ key: `C${i}`, ...figures(String(20 - i)) }))
		const option = chartOption(report(groups), false)
		const yAxis = option.yAxis as { type: string; data: string[] }
		const series = (option.series as { data: number[]; barMaxWidth: number }[])[0]
		expect(yAxis.type).toBe("category")
		expect(yAxis.data).toHaveLength(USAGE_CHART_MAX_BARS)
		expect(yAxis.data.at(-1)).toBe("C0") // the top of a category y axis is its last entry
		expect(series.data.at(-1)).toBe(20)
		expect(series.barMaxWidth).toBe(24)
	})

	it("days are columns in date order, every one", () => {
		const groups = ["2026-10-14", "2026-10-15", "2026-10-16"].map(d => ({ key: d, ...figures("0.1") }))
		const option = chartOption(report(groups, { group_by: "day" }), true)
		expect((option.xAxis as { data: string[] }).data).toEqual(["2026-10-14", "2026-10-15", "2026-10-16"])
		expect((option.series as { itemStyle: { color: string } }[])[0].itemStyle.color).toBe("#C98500")
	})

	it("nothing to draw is no option", () => {
		expect(buildUsageChartOption(report([]), STYLE, false)).toBeNull()
	})

	it("no axis label is a dollar figure: amounts are parsed only to size the bars", () => {
		for (const groupBy of ["customer", "day"] as const) {
			const groups = [
				{ key: "2026-10-15", ...figures("0.1") },
				{ key: "2026-10-16", ...figures("0.2") }
			]
			const option = chartOption(report(groups, { group_by: groupBy }), false)
			const axes = [option.xAxis, option.yAxis] as ValueAxisLike[]
			for (const axis of axes) {
				if (axis.type === "value") {
					expect(axis.axisLabel?.show).toBe(false)
					expect(axis.axisLabel?.formatter).toBeUndefined()
				}
			}
			expect(JSON.stringify(option)).not.toMatch(/\$\d/)
		}
	})

	it("the tooltip shows the API's string as it is, escaped, and says when it is incomplete", () => {
		const html = usageTooltipHtml({ label: "<img src=x onerror=alert(1)>", cost: "0.30", complete: false })
		expect(html).toContain("$0.30")
		expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;")
		expect(html).not.toContain("<img")
		expect(html).toContain("incomplete")
		const option = chartOption(report([{ key: "ACME", ...figures("0.1") }]), false)
		const formatter = (option.tooltip as { formatter: (p: unknown) => string }).formatter
		expect(formatter({ dataIndex: 0 })).toContain("$0.1")
	})

	it("its summary uses the strings too", () => {
		expect(usageChartSummary(report([{ key: "ACME", ...figures("0.1") }]))).toContain("total $0.3")
	})
})

function span(id: string, extra: Partial<TalonTimelineSpan> = {}): TalonTimelineSpan {
	return {
		span_id: id,
		trace_id: "a".repeat(32),
		parent_id: null,
		kind: "AGENT",
		name: "agent run",
		start_time: "2026-10-16T08:00:00.000000Z",
		end_time: "2026-10-16T08:00:10.000000Z",
		duration_ms: 10_000,
		status_code: "OK",
		stage: null,
		role: null,
		model: null,
		tool: null,
		prompt_tokens: null,
		completion_tokens: null,
		total_tokens: null,
		cache_read_tokens: null,
		cache_write_tokens: null,
		...extra
	}
}

describe("the run timeline layout", () => {
	it("reads the DTO's microsecond times", () => {
		expect(timeMs("2026-10-16T08:00:01.500000Z")).toBe(Date.parse("2026-10-16T08:00:01.500Z"))
	})

	it("nests by parent, siblings by start, and places bars on one axis", () => {
		const layout = layoutTimeline([
			span("c2", {
				parent_id: "r",
				start_time: "2026-10-16T08:00:05.000000Z",
				end_time: "2026-10-16T08:00:10.000000Z"
			}),
			span("r", { stage: "S5" }),
			span("c1", {
				parent_id: "r",
				start_time: "2026-10-16T08:00:01.000000Z",
				end_time: "2026-10-16T08:00:03.500000Z"
			}),
			span("g", {
				parent_id: "c1",
				start_time: "2026-10-16T08:00:02.000000Z",
				end_time: "2026-10-16T08:00:02.000000Z"
			})
		])
		const [lane] = layout.lanes
		expect(lane.label).toBe("Trace 1 · S5")
		expect(lane.rows.map(r => [r.span.span_id, r.depth])).toEqual([
			["r", 0],
			["c1", 1],
			["g", 2],
			["c2", 1]
		])
		const at = Object.fromEntries(lane.rows.map(r => [r.span.span_id, [r.leftPct, r.widthPct]]))
		expect(at.r).toEqual([0, 100])
		expect(at.c1).toEqual([10, 25])
		expect(at.c2).toEqual([50, 50])
		expect(at.g).toEqual([20, TIMELINE_MIN_WIDTH_PCT]) // an instant is still seen
	})

	it("a lane per trace in start order; a parent outside the trace and a cycle never lose a span", () => {
		const other = "b".repeat(32)
		const layout = layoutTimeline([
			span("late", { trace_id: other, start_time: "2026-10-16T08:00:05.000000Z" }),
			span("x", { parent_id: "y" }),
			span("y", { parent_id: "x" }),
			span("orphan", { parent_id: "ffffffffffffffff" })
		])
		expect(layout.lanes.map(l => l.traceId)).toEqual(["a".repeat(32), other])
		expect(layout.lanes[0].rows.map(r => r.span.span_id).sort()).toEqual(["orphan", "x", "y"])
	})

	it("token counts for reading", () => {
		const format = (n: number) => n.toLocaleString("en-US")
		expect(spanTokens({ prompt_tokens: 1200, completion_tokens: 300, total_tokens: 1500 }, format)).toBe(
			"1,200 in · 300 out"
		)
		expect(spanTokens({ prompt_tokens: null, completion_tokens: null, total_tokens: 9 }, format)).toBe("9 tokens")
		expect(spanTokens({ prompt_tokens: null, completion_tokens: null, total_tokens: null }, format)).toBeNull()
	})
})

describe("the run timeline's edges", () => {
	it("an instant at the axis end still has room: its left is clamped before it is sized", () => {
		const layout = layoutTimeline([
			span("r"),
			span("end", {
				parent_id: "r",
				start_time: "2026-10-16T08:00:10.000000Z",
				end_time: "2026-10-16T08:00:10.000000Z"
			})
		])
		const end = layout.lanes[0].rows.find(r => r.span.span_id === "end")
		expect(end?.leftPct).toBe(100 - TIMELINE_MIN_WIDTH_PCT)
		expect(end?.widthPct).toBe(TIMELINE_MIN_WIDTH_PCT)
		for (const row of layout.lanes[0].rows) expect(row.leftPct + row.widthPct).toBeLessThanOrEqual(100)
	})

	it("a span ending before it starts is an instant, never a negative bar", () => {
		const layout = layoutTimeline([
			span("r"),
			span("back", {
				parent_id: "r",
				start_time: "2026-10-16T08:00:05.000000Z",
				end_time: "2026-10-16T08:00:02.000000Z"
			})
		])
		const back = layout.lanes[0].rows.find(r => r.span.span_id === "back")
		expect(back?.leftPct).toBe(50)
		expect(back?.widthPct).toBe(TIMELINE_MIN_WIDTH_PCT)
	})

	it("spans whose times don't parse are counted, not placed", () => {
		const layout = layoutTimeline([
			span("r"),
			span("bad", { start_time: "yesterday" }),
			span("worse", { end_time: "" })
		])
		expect(layout.unreadable).toBe(2)
		expect(layout.lanes[0].rows.map(r => r.span.span_id)).toEqual(["r"])
		expect(layoutTimeline([span("bad", { start_time: "x" })])).toMatchObject({ lanes: [], unreadable: 1 })
	})
})

describe("what a span ran", () => {
	it("names a tool by CoPilot's label when it has one, else by name, else the model", () => {
		expect(spanSubject({ tool: "tavily_search", tool_label: "Web search (Tavily)", model: null })).toBe(
			"Web search (Tavily)"
		)
		expect(spanSubject({ tool: "siem_search", tool_label: null, model: null })).toBe("siem_search")
		expect(spanSubject({ tool: "siem_search", model: null })).toBe("siem_search")
		expect(spanSubject({ tool: null, model: "claude-sonnet-5-5" })).toBe("claude-sonnet-5-5")
	})
})

describe("the warning threshold", () => {
	it("is the API's share as a percentage, moved on the string, never through a float", () => {
		expect(warnAtPercent("0.805")).toBe("80.5%")
		expect(warnAtPercent("0.995")).toBe("99.5%")
		expect(warnAtPercent("0.8")).toBe("80%")
		expect(warnAtPercent("0.80")).toBe("80%")
		expect(warnAtPercent("0.07")).toBe("7%")
		expect(warnAtPercent("1")).toBe("100%")
		expect(warnAtPercent("0.123456")).toBe("12.3456%")
		for (const bad of [undefined, null, "", "-0.8", "8e-1", "0.8%", " 0.8"]) expect(warnAtPercent(bad)).toBe("80%")
	})
})

describe("the budget form", () => {
	it("takes what CoPilot takes: a positive decimal, at most 12 places, at most 1000000000", () => {
		for (const ok of ["25", "12.50", "0.5", "0.000000000001", "1000000000", "1000000000.000", " 7 "]) {
			expect(budgetAmountProblem(ok), ok).toBeNull()
		}
		for (const bad of ["", "0", "0.00", "-1", "+1", "1e3", "01", "1.", ".5", "1.0000000000001", "1,000", "abc"]) {
			expect(budgetAmountProblem(bad), bad).not.toBeNull()
		}
		expect(budgetAmountProblem("1000000000.01")).toBe("At most 1000000000 USD.")
		expect(budgetAmountProblem("9999999999")).toBe("At most 1000000000 USD.")
	})

	it("opens on what the window is now, and sends both windows as typed", () => {
		const entry = (source: string, limit: string | null) =>
			({
				window: "day",
				period: "2026-10-16",
				limit_usd: limit,
				source,
				spent_usd: null,
				remaining_usd: null,
				warning: false,
				exhausted: false
			}) as never
		expect(windowFormFromEntry(entry("override", "12.50"))).toEqual({ choice: "amount", amount: "12.50" })
		expect(windowFormFromEntry(entry("unlimited", null))).toEqual({ choice: "unlimited", amount: "" })
		expect(windowFormFromEntry(entry("default", "25"))).toEqual({ choice: "default", amount: "" })
		expect(budgetPayload({ choice: "amount", amount: " 12.50 " }, { choice: "default", amount: "9" })).toEqual({
			daily_usd: "12.50",
			monthly_usd: null
		})
		expect(budgetPayload({ choice: "unlimited", amount: "" }, { choice: "amount", amount: "300" })).toEqual({
			daily_usd: "unlimited",
			monthly_usd: "300"
		})
		expect(describeWindow({ choice: "default", amount: "" })).toBe("the default")
		expect(limitText(entry("unset", null))).toBe("No limit")
		expect(limitText(entry("override", "0.1"))).toBe("$0.1")
	})
})
