import type { OverviewTrendHour } from "@/types/portal"
import { describe, expect, it } from "vitest"
import { formatNet, parseTrendRange, trendDays, trendTotals } from "../trend"

function hour(iso: string, counts: Partial<Omit<OverviewTrendHour, "hour">> = {}): OverviewTrendHour {
	return { hour: iso, alerts_opened: 0, alerts_closed: 0, cases_opened: 0, cases_closed: 0, ...counts }
}

describe("overview trend (#1273)", () => {
	it("reads the period from the URL, and anything else as the default", () => {
		expect(parseTrendRange("7d")).toBe("7d")
		expect(parseTrendRange(["30d", "7d"])).toBe("30d")
		expect(parseTrendRange("90d")).toBe("30d")
		expect(parseTrendRange(undefined)).toBe("30d")
		expect(parseTrendRange(null)).toBe("30d")
	})

	it("lists every day of the period, up to the one holding the latest hour", () => {
		const days = trendDays({ range: "7d", until: "2026-10-17T10:00:00Z", hours: [] }, "UTC")
		expect(days.map(day => day.day)).toEqual([
			"2026-10-11",
			"2026-10-12",
			"2026-10-13",
			"2026-10-14",
			"2026-10-15",
			"2026-10-16",
			"2026-10-17"
		])
		expect(days.every(day => day.alerts.opened === 0 && day.cases.closed === 0)).toBe(true)
		expect(trendDays({ range: "30d", until: "2026-10-17T10:00:00Z", hours: [] }, "UTC")).toHaveLength(30)
	})

	it("ends on the day of the latest counted hour, not the day `until` falls on", () => {
		// until = midnight UTC: the last hour counted is 23:00 of the 16th.
		const days = trendDays({ range: "7d", until: "2026-10-17T00:00:00Z", hours: [] }, "UTC")
		expect(days.at(-1)!.day).toBe("2026-10-16")
	})

	it("sums each UTC hour into the viewer's day", () => {
		const hours = [
			hour("2026-10-16T21:00:00Z", { alerts_opened: 2 }), // 23:00 in Rome (UTC+2): still the 16th
			hour("2026-10-16T22:00:00Z", { alerts_opened: 1, alerts_closed: 3 }), // 00:00 in Rome: the 17th
			hour("2026-10-17T08:00:00Z", { cases_opened: 1, cases_closed: 1 })
		]
		const days = trendDays({ range: "7d", until: "2026-10-17T09:00:00Z", hours }, "Europe/Rome")
		const byDay = Object.fromEntries(days.map(day => [day.day, day]))
		expect(byDay["2026-10-16"]!.alerts).toEqual({ opened: 2, closed: 0 })
		expect(byDay["2026-10-17"]!.alerts).toEqual({ opened: 1, closed: 3 })
		expect(byDay["2026-10-17"]!.cases).toEqual({ opened: 1, closed: 1 })

		// The same hours in New York (UTC−4) all fall on the 16th, but the 08:00Z one.
		const ny = Object.fromEntries(
			trendDays({ range: "7d", until: "2026-10-17T09:00:00Z", hours }, "America/New_York").map(day => [day.day, day])
		)
		expect(ny["2026-10-16"]!.alerts).toEqual({ opened: 3, closed: 3 })
		expect(ny["2026-10-17"]!.cases).toEqual({ opened: 1, closed: 1 })
	})

	it("follows a DST change: the same UTC hour starts a different local day on each side", () => {
		// Rome leaves summer time at 01:00Z on 25 October: midnight is 22:00Z before, 23:00Z after.
		const hours = [
			hour("2026-10-24T22:00:00Z", { alerts_opened: 1 }), // 00:00 CEST, the 25th
			hour("2026-10-25T22:00:00Z", { alerts_opened: 10 }), // 23:00 CET, still the 25th
			hour("2026-10-25T23:00:00Z", { alerts_opened: 100 }) // 00:00 CET, the 26th
		]
		const days = trendDays({ range: "7d", until: "2026-10-26T01:00:00Z", hours }, "Europe/Rome")
		const byDay = Object.fromEntries(days.map(day => [day.day, day.alerts.opened]))
		expect(byDay).toMatchObject({ "2026-10-25": 11, "2026-10-26": 100 })
	})

	it("leaves out the extra day the server sends for the timezones ahead of UTC", () => {
		const days = trendDays(
			{
				range: "7d",
				until: "2026-10-17T10:00:00Z",
				hours: [hour("2026-10-09T10:00:00Z", { alerts_opened: 5 }), hour("2026-10-11T00:00:00Z", { alerts_opened: 1 })]
			},
			"UTC"
		)
		expect(trendTotals(days, "alerts").opened).toBe(1)
	})

	it("totals a period, and signs what it added to the backlog", () => {
		const days = trendDays(
			{
				range: "7d",
				until: "2026-10-17T10:00:00Z",
				hours: [
					hour("2026-10-15T10:00:00Z", { alerts_opened: 4, alerts_closed: 1, cases_closed: 2 }),
					hour("2026-10-16T10:00:00Z", { alerts_opened: 1, alerts_closed: 1 })
				]
			},
			"UTC"
		)
		expect(trendTotals(days, "alerts")).toEqual({ opened: 5, closed: 2, net: 3 })
		expect(trendTotals(days, "cases")).toEqual({ opened: 0, closed: 2, net: -2 })
		expect([formatNet(3), formatNet(-2), formatNet(0)]).toEqual(["+3", "−2", "0"])
	})
})
