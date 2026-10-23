/**
 * The Memory tab's pure helpers: the forget rule, the date filter, the breakdowns, the growth chart
 * (a null day is a gap, never a zero; the tooltip escapes API strings) and how a failure is told
 * apart: CoPilot's own "Not Found" (Talon v2 off) from talon-analyst's (no memory API).
 */
import type { TalonMemoryDrawer, TalonMemoryStats } from "@/types/talonMemory"
import { readdirSync, readFileSync } from "node:fs"
import { join } from "node:path"
import { AxiosError, AxiosHeaders } from "axios"
import { describe, expect, it } from "vitest"
import { memoryFailure } from "@/api/endpoints/talonMemory"
import {
	breakdown,
	buildGrowthOption,
	canForget,
	dateParams,
	formatCount,
	growthSummary,
	growthTotal,
	OLD_TALON_MEMORY_TEXT,
	problemState,
	ROOMS,
	SOURCES
} from "../memory"

function drawer(overrides: Partial<TalonMemoryDrawer> = {}): TalonMemoryDrawer {
	return {
		drawer_id: "drawer_ACME_false_positives_0123",
		openable: true,
		room: "false_positives",
		source: "review_one_off",
		source_ref: null,
		filed_at: "2026-10-21T10:00:00Z",
		durable: false,
		testing_hidden: false,
		visible_to_investigations: true,
		preview: "p",
		content: "c",
		forgettable: true,
		why_not_forgettable: null,
		why_hidden: null,
		...overrides
	}
}

function stats(growth: TalonMemoryStats["growth"]): TalonMemoryStats {
	return {
		success: true,
		customer_code: "ACME",
		total: 5,
		checked_at: null,
		rooms: { alerts: 4, false_positives: 2, threat_intel: null, assets: 0, environment: 1, other: 0 },
		sources: { investigation: 3, review_durable: 1, review_one_off: 1, chat_remember: 0, other: null },
		testing_hidden: 1,
		growth
	}
}

function axiosError(status: number, data: unknown) {
	const headers = new AxiosHeaders()
	return new AxiosError("x", "ERR", undefined, undefined, {
		status,
		statusText: "",
		data,
		headers,
		config: { headers }
	})
}

const STYLE = {
	"fg-secondary-color": "#666",
	"border-color": "#ddd",
	"bg-default-color": "#fff",
	"font-family": "sans"
}

describe("the forget rule", () => {
	it("allows one-off review and chat remember lessons Talon calls forgettable", () => {
		expect(canForget(drawer())).toBe(true)
		expect(canForget(drawer({ source: "chat_remember" }))).toBe(true)
	})

	it.each([
		[{ source: "investigation" as const }],
		[{ source: "review_durable" as const }],
		[{ source: "other" as const }],
		[{ durable: true }],
		[{ forgettable: false }],
		[{ openable: false }]
	])("refuses %o", overrides => {
		expect(canForget(drawer(overrides))).toBe(false)
	})

	it("refuses nothing loaded", () => {
		expect(canForget(null)).toBe(false)
	})
})

describe("the date filter", () => {
	it("sends since inclusive and before as the day after the last day", () => {
		expect(dateParams(["2026-10-01", "2026-10-31"])).toEqual({ since: "2026-10-01", before: "2026-11-01" })
		expect(dateParams(["2026-12-31", "2026-12-31"])).toEqual({ since: "2026-12-31", before: "2027-01-01" })
		expect(dateParams(null)).toEqual({ since: null, before: null })
	})
})

describe("breakdowns and counts", () => {
	it("keeps every category in order, null as no data, bars relative to the largest", () => {
		const rows = breakdown(stats([]).rooms, ROOMS)
		expect(rows.map(r => r.key)).toEqual([
			"alerts",
			"false_positives",
			"threat_intel",
			"assets",
			"environment",
			"other"
		])
		expect(rows[0].share).toBe(1)
		expect(rows[1].share).toBe(0.5)
		expect(rows[2]).toMatchObject({ count: null, share: 0 })
		expect(formatCount(rows[2].count)).toBe("no data")
		expect(breakdown(stats([]).sources, SOURCES).map(r => r.label)).toContain('Chat "remember"')
	})

	it("sums growth only when Talon reported a day", () => {
		expect(growthTotal(stats([]))).toBeNull()
		expect(growthTotal(stats([{ date: "2026-10-01", filed: null }]))).toBeNull()
		expect(
			growthTotal(
				stats([
					{ date: "2026-10-01", filed: 2 },
					{ date: "2026-10-02", filed: null },
					{ date: "2026-10-03", filed: 3 }
				])
			)
		).toBe(5)
		expect(growthSummary(stats([]))).toBe("Memories filed per day: no data")
	})
})

describe("the growth chart", () => {
	it("is null without data, one amber series with a gap for a null day", () => {
		expect(buildGrowthOption(stats([]), STYLE, false)).toBeNull()
		const option = buildGrowthOption(
			stats([
				{ date: "2026-10-01", filed: 2 },
				{ date: "2026-10-02", filed: null }
			]),
			STYLE,
			false
		)
		const series = (option?.series as { data: unknown[]; itemStyle: { color: string } }[])[0]
		expect(series.data).toEqual([2, "-"])
		expect(series.itemStyle.color).toBe("#A87400")
		expect(
			(
				buildGrowthOption(stats([{ date: "2026-10-01", filed: 1 }]), STYLE, true)?.series as {
					itemStyle: { color: string }
				}[]
			)[0].itemStyle.color
		).toBe("#C98500")
	})

	it("says no data in the tooltip for a null day", () => {
		const option = buildGrowthOption(stats([{ date: "2026-10-02", filed: null }]), STYLE, false)
		const formatter = (option?.tooltip as { formatter: (p: unknown) => string }).formatter
		expect(formatter({ dataIndex: 0 })).toContain("no data")
	})
})

describe("telling failures apart", () => {
	it("copilot's own Not Found is Talon v2 off", () => {
		const failure = memoryFailure(axiosError(404, { detail: "Not Found" }))
		expect(failure.code).toBe("v2_off")
		expect(problemState(failure)?.kind).toBe("v2_off")
	})

	it("talon-analyst's 404 is an old Talon", () => {
		const failure = memoryFailure(axiosError(404, { detail: OLD_TALON_MEMORY_TEXT, code: "unsupported" }))
		expect(failure).toEqual({ status: 404, code: "unsupported", detail: OLD_TALON_MEMORY_TEXT })
		expect(problemState(failure)).toMatchObject({ kind: "unsupported", text: OLD_TALON_MEMORY_TEXT })
	})

	it("anything else is an error with CoPilot's text and status", () => {
		const failure = memoryFailure(axiosError(502, { detail: "Talon request failed", code: "unavailable" }))
		expect(problemState(failure)).toMatchObject({ kind: "error", text: "Talon request failed (HTTP 502)" })
		expect(memoryFailure(new Error("x")).code).toBe("unknown")
		expect(memoryFailure(axiosError(500, { detail: "x", code: "<script>" })).code).toBe("unknown")
	})
})

describe("rendering", () => {
	it("no Memory component uses v-html (markdown goes through the Markdown component only)", () => {
		const dir = join(__dirname, "..")
		for (const file of readdirSync(dir).filter(name => name.endsWith(".vue"))) {
			expect(readFileSync(join(dir, file), "utf8"), file).not.toMatch(/v-html|innerHTML/)
		}
	})
})
