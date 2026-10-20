import { describe, expect, it } from "vitest"
import { filtersFromQuery } from "@/components/alerts/filters/alertsFilters"
import {
	alertsLink,
	barWidth,
	buildKpis,
	countDelta,
	DEFAULT_RANGE,
	hasActivity,
	panelMax,
	rangeFromQuery,
	rateDelta,
	sliceLabel,
	windowOf,
	withRange
} from "../activity"
import { activityFixture } from "./fixtures"

/** The Activity page's logic (#1284): what the customer reads, and where a click takes them. */
describe("activity: the range", () => {
	it("reads the range from the URL, anything else being the default", () => {
		expect(rangeFromQuery("7d")).toBe("7d")
		expect(rangeFromQuery(["90d", "7d"])).toBe("90d")
		expect(rangeFromQuery("1y")).toBe(DEFAULT_RANGE)
		expect(rangeFromQuery(undefined)).toBe("30d")
	})

	it("writes the range and leaves the default out of the URL", () => {
		expect(withRange({ tab: "x", range: "7d" }, "30d")).toEqual({ tab: "x" })
		expect(withRange({ tab: "x" }, "90d")).toEqual({ tab: "x", range: "90d" })
	})
})

describe("activity: what moved", () => {
	it("says how a count moved, neutrally, and that a slice is new", () => {
		expect(countDelta(12, 9)).toEqual({ text: "+3", direction: "up" })
		expect(countDelta(3, 5)).toEqual({ text: "−2", direction: "down" })
		expect(countDelta(4, 4)).toEqual({ text: "0", direction: "flat" })
		expect(countDelta(2, 0)).toEqual({ text: "new", direction: "up" })
		expect(countDelta(0, 0)).toEqual({ text: "0", direction: "flat" })
	})

	it("moves rates in points, and has no change without both rates", () => {
		expect(rateDelta(25, 30.5)).toEqual({ points: -5.5, text: "−5.5 pts", direction: "down" })
		expect(rateDelta(66.7, 50)).toEqual({ points: 16.7, text: "+16.7 pts", direction: "up" })
		expect(rateDelta(25, null).points).toBeNull()
	})
})

describe("activity: bars", () => {
	it("scales a panel to its longest bar, either period", () => {
		expect(panelMax([{ key: "a", label: null, count: 3, previous: 9 }])).toBe(9)
		expect(panelMax([])).toBe(0)
	})

	it("keeps a small count visible beside a large one, and nothing as nothing", () => {
		expect(barWidth(500, 500)).toBe(100)
		expect(barWidth(1, 500)).toBe(2)
		expect(barWidth(0, 500)).toBe(0)
		expect(barWidth(5, 0)).toBe(0)
	})
})

describe("activity: links to the alerts list", () => {
	const activity = activityFixture()

	it("lists the period's alerts with the window the page counted in", () => {
		const link = alertsLink(activity, "current", null) as { name: string; query: Record<string, string> }
		expect(link.name).toBe("AlertsList")
		const filters = filtersFromQuery(link.query)
		expect([filters.openedFrom, filters.openedBefore]).toEqual(["2026-09-01T12:00:00Z", "2026-10-01T12:00:00Z"])
	})

	it("asks the previous period for its own window", () => {
		expect(windowOf(activity, "previous")).toEqual({ from: "2026-08-02T12:00:00Z", before: "2026-09-01T12:00:00Z" })
	})

	it("names each slice exactly: source, asset, tag and detection", () => {
		const read = (kind: "source" | "asset" | "tag" | "detection", key: string) =>
			filtersFromQuery((alertsLink(activity, "current", kind, key) as { query: Record<string, string> }).query)
		expect(read("source", "wazuh").source).toBe("wazuh")
		expect(read("asset", "web-01").asset).toBe("web-01")
		expect(read("tag", "vip").tags).toEqual(["vip"])
		const detection = read("detection", "Brute force")
		// Exact, not the title search: a click lists only that detection.
		expect([detection.detection, detection.title]).toEqual(["Brute force", null])
	})

	it("links nowhere without a window", () => {
		expect(alertsLink(activityFixture({ since: null }), "current", "source", "wazuh")).toBeNull()
	})
})

describe("activity: labels and headline", () => {
	it("shows the API's label, the key, or a status in the portal's words", () => {
		expect(sliceLabel({ key: "INC", label: "Incident", count: 1, previous: 0 })).toBe("Incident")
		expect(sliceLabel({ key: "wazuh", label: null, count: 1, previous: 0 })).toBe("wazuh")
		expect(sliceLabel({ key: "PENDING_CUSTOMER", label: null, count: 1, previous: 0 }, "status")).toBe("Waiting on you")
	})

	it("builds the four headline figures with their changes", () => {
		const kpis = buildKpis(activityFixture())
		expect(kpis.map(kpi => [kpi.key, kpi.value, kpi.caption])).toEqual([
			["alerts", "12", "9 the period before"],
			["cases", "2", "1 the period before"],
			["false-positives", "25%", "of 8 reviewed"],
			["coverage", "66.7%", "8 of 12 alerts"]
		])
		expect(kpis[0]!.delta).toEqual({ text: "+3", direction: "up" })
		// Nothing was reviewed before: no change in points, never "−25 pts".
		expect(kpis[2]!.delta).toBeNull()
		expect(kpis[3]!.delta?.text).toBe("+66.7 pts")
	})

	it("says nothing was reviewed rather than 0%", () => {
		const quiet = activityFixture()
		quiet.verdicts.current = { ...quiet.verdicts.previous, total: 0, untriaged: 0, coverage_rate: null }
		const [, , fp, coverage] = buildKpis(quiet)
		expect([fp!.value, fp!.caption]).toEqual(["—", "nothing reviewed yet"])
		expect([coverage!.value, coverage!.caption]).toEqual(["—", "no alerts this period"])
	})

	it("knows when neither period had anything", () => {
		expect(hasActivity(activityFixture())).toBe(true)
		const empty = activityFixture()
		empty.alerts.opened = { count: 0, previous: 0 }
		empty.cases.opened = { count: 0, previous: 0 }
		expect(hasActivity(empty)).toBe(false)
	})
})
