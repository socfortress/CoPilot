/**
 * The health dashboard's pure helpers: the banner's verdict, grouping, the uptime cells (a merged
 * cell keeps the worst status), and formatting that never turns a missing value into 0.
 */
import { describe, expect, it } from "vitest"
import {
	banner,
	componentStatus,
	costValue,
	formatAgo,
	formatCeiling,
	formatCount,
	formatDuration,
	formatLatency,
	formatSwitch,
	formatUsdText,
	formatWriteback,
	groupComponents,
	OLD_TALON_TEXT,
	secondsSince,
	uptimeCells,
	uptimeSummary,
	worstStatus
} from "../health"
import { component, healthReport, must, oldTalonReport, unreachableReport } from "./fixtures"

describe("talon health helpers", () => {
	it("the banner follows talon-analyst's verdict", () => {
		expect(banner(healthReport()).title).toBe("Degraded")
		const ok = healthReport()
		must(ok.health.data).status = "ok"
		expect(banner(ok)).toMatchObject({ title: "All systems operational", tone: "good" })
		must(ok.health.data).status = "down"
		expect(banner(ok)).toMatchObject({ title: "Down", tone: "bad" })
	})

	it("without a verdict, the banner says what CoPilot could tell", () => {
		expect(banner(unreachableReport())).toMatchObject({
			title: "Down",
			tone: "bad",
			reason: "Talon could not be reached (ConnectError)"
		})
		expect(banner(oldTalonReport())).toMatchObject({ title: "Status unknown", reason: OLD_TALON_TEXT })
		const refused = oldTalonReport()
		refused.copilot.auth = { ok: false, latency_ms: null, status_code: 401, error: "Talon refused CoPilot's API key (401)" }
		expect(banner(refused)).toMatchObject({ title: "Down", reason: "Talon refused CoPilot's API key (401)" })
		const none = unreachableReport()
		none.copilot.connector = { exists: true, configured: false, verified: false, url: null }
		expect(banner(none).title).toBe("Talon is not connected")
		expect(banner(null).title).toBe("Checking Talon…")
	})

	it("groups components Core, MCP servers, Model, and anything else last", () => {
		const groups = groupComponents([
			component("intel_mcp", { group: "mcp" }),
			component("api"),
			component("model_provider", { group: "model" }),
			component("future", { group: "weird" as never })
		])
		expect(groups.map(g => g.title)).toEqual(["Core", "MCP servers", "Model", "Other"])
		expect(groups[3].components.map(c => c.id)).toEqual(["future"])
		expect(groupComponents(null)).toEqual([])
	})

	it("an unknown status is unknown, never ok", () => {
		expect(componentStatus("ok")).toBe("ok")
		expect(componentStatus("purple")).toBe("unknown")
		expect(componentStatus(undefined)).toBe("unknown")
	})

	it("a merged uptime cell keeps its worst status, and empty buckets are no data", () => {
		expect(worstStatus({ ok: 10, warn: 1, fail: 0 })).toBe("warn")
		expect(worstStatus({ ok: 10, warn: 1, fail: 1 })).toBe("fail")
		expect(worstStatus({ ok: null, warn: null, fail: null })).toBe("none")
		const buckets = Array.from({ length: 2016 }, (_, i) => ({
			t: `t${i}`,
			ok: 1,
			warn: 0,
			fail: i === 1000 ? 1 : 0
		}))
		const cells = uptimeCells(buckets, 84)
		expect(cells.length).toBe(84)
		expect(cells.filter(c => c.status === "fail")).toHaveLength(1)
		expect(uptimeSummary(cells)).toBe("1 failing of 84")
		expect(uptimeSummary(uptimeCells([{ t: "a", ok: 3, warn: 0, fail: 0 }]))).toBe("all 1 OK")
		expect(uptimeSummary([])).toBe("no data")
	})

	it("formats without inventing values", () => {
		expect(formatLatency(8.4)).toBe("8 ms")
		expect(formatLatency(1530)).toBe("1.5 s")
		expect(formatLatency(null)).toBe("—")
		expect(formatDuration(93_600)).toBe("1 d 2 h")
		expect(formatDuration(42)).toBe("42 s")
		expect(formatDuration(null)).toBeNull()
		expect(formatCount(null)).toBe("no data")
		expect(formatCount(0)).toBe("0")
		expect(formatSwitch(true)).toBe("On")
		expect(formatSwitch(false)).toBe("Off")
		expect(formatSwitch("shadow")).toBe("shadow")
		expect(formatSwitch(null)).toBe("Not reported")
		expect(formatUsdText("0.30")).toBe("$0.30")
		expect(formatUsdText("unlimited")).toBe("Unlimited")
		expect(formatUsdText(null)).toBe("no data")
	})

	it("checked N seconds ago, from a naive or zoned UTC time", () => {
		const now = Date.parse("2026-10-22T08:00:30Z")
		expect(formatAgo(secondsSince("2026-10-22T08:00:00", now))).toBe("checked 30s ago")
		expect(formatAgo(secondsSince("2026-10-22T07:58:00Z", now))).toBe("checked 2m ago")
		expect(formatAgo(secondsSince("garbage", now))).toBe("not checked yet")
	})

	it("budgets: a null ceiling is unlimited; write-back modes as words", () => {
		expect(formatCeiling(null)).toBe("Unlimited")
		expect(formatCeiling("25.00")).toBe("$25.00")
		expect(formatWriteback("off")).toBe("Off")
		expect(formatWriteback("shadow")).toBe("Shadow")
		expect(formatWriteback("live")).toBe("Live")
		expect(formatWriteback("future")).toBe("future")
		expect(formatWriteback(null)).toBe("Not reported")
		expect(costValue("1.25")).toBe(1.25)
		expect(costValue("nope")).toBeNull()
		expect(costValue(null)).toBeNull()
	})
})
