import type { AlertsFilters } from "../alertsFilters"
import { describe, expect, it } from "vitest"
import {
	activeFilterTypes,
	dayToTimestamp,
	EMPTY_ALERTS_FILTERS,
	filtersFromQuery,
	filtersKey,
	filtersToParams,
	filtersToQuery,
	hasFilters,
	instant,
	isDay,
	isLinkFilter,
	openedLabel,
	timestampToDay,
	withFilters,
	withoutFilter
} from "../alertsFilters"

const ALL: AlertsFilters = {
	title: "login",
	status: "OPEN",
	source: "wazuh",
	asset: "web-01",
	tags: ["phishing", "vip"],
	from: "2026-10-01",
	to: "2026-10-13",
	detection: "Brute force",
	openedFrom: "2026-09-01T12:00:00Z",
	openedBefore: "2026-10-01T12:00:00Z"
}

/** The alerts list's filters and the URL (#1245): the query string is their only store. */
describe("alerts filters ↔ query string", () => {
	it("reads every filter back from the query it writes", () => {
		const query = filtersToQuery(ALL)
		expect(query).toEqual({
			title: "login",
			status: "OPEN",
			source: "wazuh",
			asset: "web-01",
			tag: ["phishing", "vip"],
			from: "2026-10-01",
			to: "2026-10-13",
			detection: "Brute force",
			opened_from: "2026-09-01T12:00:00Z",
			opened_before: "2026-10-01T12:00:00Z"
		})
		expect(filtersFromQuery(query as Record<string, string | string[]>)).toEqual(ALL)
	})

	it("an empty query is no filter, and no filter leaves no key", () => {
		expect(filtersFromQuery({})).toEqual(EMPTY_ALERTS_FILTERS)
		expect(filtersToQuery(EMPTY_ALERTS_FILTERS)).toEqual({})
		expect(filtersToQuery({ ...EMPTY_ALERTS_FILTERS, title: "   " })).toEqual({})
	})

	it("one tag is a plain value in the URL, several a repeated key", () => {
		expect(filtersFromQuery({ tag: "vip" }).tags).toEqual(["vip"])
		expect(filtersFromQuery({ tag: ["vip", "vip", " ", "ops"] }).tags).toEqual(["vip", "ops"])
	})

	it("keeps the SLA page's `?status=` link working", () => {
		expect(filtersFromQuery({ status: "PENDING_CUSTOMER" }).status).toBe("PENDING_CUSTOMER")
	})

	it("ignores what it cannot read rather than sending it", () => {
		const filters = filtersFromQuery({ status: "ESCALATED", from: "2026-02-30", to: "yesterday", title: "" })
		expect(filters).toEqual(EMPTY_ALERTS_FILTERS)
	})

	it("reads a range written the wrong way round as that range", () => {
		const filters = filtersFromQuery({ from: "2026-10-13", to: "2026-10-01" })
		expect([filters.from, filters.to]).toEqual(["2026-10-01", "2026-10-13"])
	})

	it("replaces the filter keys and keeps every other key of the query", () => {
		const query = withFilters(
			{ status: "OPEN", tag: ["x"], page: "3" },
			{ ...EMPTY_ALERTS_FILTERS, source: "wazuh" }
		)
		expect(query).toEqual({ page: "3", source: "wazuh" })
	})

	it("is keyed by what it asks, not by its spelling", () => {
		expect(filtersKey(filtersFromQuery({ title: " login " }))).toBe(
			filtersKey({ ...EMPTY_ALERTS_FILTERS, title: "login" })
		)
		expect(filtersKey(ALL)).not.toBe(filtersKey({ ...ALL, tags: ["vip"] }))
	})
})

describe("alerts filters: which are in use", () => {
	it("lists the menu filters in use, in menu order", () => {
		expect(activeFilterTypes(ALL)).toEqual(["detection", "opened", "status", "source", "asset", "tag", "date"])
		expect(activeFilterTypes({ ...EMPTY_ALERTS_FILTERS, to: "2026-10-01", source: "x" })).toEqual([
			"source",
			"date"
		])
		expect(activeFilterTypes({ ...EMPTY_ALERTS_FILTERS, title: "x" })).toEqual([])
	})

	it("counts the title as a filter", () => {
		expect(hasFilters({ ...EMPTY_ALERTS_FILTERS, title: "x" })).toBe(true)
		expect(hasFilters(EMPTY_ALERTS_FILTERS)).toBe(false)
	})

	it("tells the links' filters from the menu's", () => {
		expect(["detection", "opened"].every(type => isLinkFilter(type as "detection"))).toBe(true)
		expect(isLinkFilter("source")).toBe(false)
		expect(hasFilters({ ...EMPTY_ALERTS_FILTERS, openedBefore: "2026-10-01T12:00:00Z" })).toBe(true)
	})

	it("removes the reached-the-SOC window as a whole, and the detection alone", () => {
		const window = withoutFilter(ALL, "opened")
		expect([window.openedFrom, window.openedBefore, window.detection]).toEqual([null, null, "Brute force"])
		expect(withoutFilter(ALL, "detection")).toEqual({ ...ALL, detection: null })
	})

	it("removes one filter at a time, the date range as a whole", () => {
		expect(withoutFilter(ALL, "tag").tags).toEqual([])
		expect(withoutFilter(ALL, "status")).toEqual({ ...ALL, status: null })
		const undated = withoutFilter(ALL, "date")
		expect([undated.from, undated.to, undated.source]).toEqual([null, null, "wazuh"])
	})
})

describe("alerts filters → API parameters", () => {
	it("names each filter as the endpoint does", () => {
		const params = filtersToParams({ ...ALL, from: null, to: null })
		expect(params).toEqual({
			alert_title: "login",
			status: "OPEN",
			source: "wazuh",
			asset_name: "web-01",
			tags: ["phishing", "vip"],
			alert_name: "Brute force",
			opened_from: "2026-09-01T12:00:00Z",
			opened_before: "2026-10-01T12:00:00Z"
		})
	})

	it("sends nothing for no filter", () => {
		expect(filtersToParams(EMPTY_ALERTS_FILTERS)).toEqual({})
	})

	it("covers both days whole, from local midnight to the last local millisecond, as UTC", () => {
		const { date_from, date_to } = filtersToParams({
			...EMPTY_ALERTS_FILTERS,
			from: "2026-10-01",
			to: "2026-10-13"
		})
		expect(new Date(date_from!).getTime()).toBe(new Date(2026, 9, 1).getTime())
		expect(new Date(date_to!).getTime()).toBe(new Date(2026, 9, 13, 23, 59, 59, 999).getTime())
		expect(date_from).toMatch(/Z$/)
	})

	it("leaves an open end open", () => {
		expect(Object.keys(filtersToParams({ ...EMPTY_ALERTS_FILTERS, from: "2026-10-01" }))).toEqual(["date_from"])
		expect(Object.keys(filtersToParams({ ...EMPTY_ALERTS_FILTERS, to: "2026-10-01" }))).toEqual(["date_to"])
	})
})

/** The Activity page's links (#1284): an exact detection and the window it counted in. */
describe("the reached-the-SOC window", () => {
	it("reads only ISO instants with a time, and keeps them as written", () => {
		expect(instant("2026-09-01T12:00:00Z")).toBe("2026-09-01T12:00:00Z")
		expect(instant("2026-09-01T12:00:00+02:00")).toBe("2026-09-01T12:00:00+02:00")
		for (const value of ["2026-09-01", "yesterday", "2026-13-45T99:99", "", null]) expect(instant(value)).toBeNull()
	})

	it("drops an empty or reversed window instead of sending one the server refuses", () => {
		const reversed = filtersFromQuery({ opened_from: "2026-10-01T12:00:00Z", opened_before: "2026-09-01T12:00:00Z" })
		expect([reversed.openedFrom, reversed.openedBefore]).toEqual([null, null])
		const empty = filtersFromQuery({ opened_from: "2026-10-01T12:00:00Z", opened_before: "2026-10-01T12:00:00Z" })
		expect([empty.openedFrom, empty.openedBefore]).toEqual([null, null])
		expect(filtersFromQuery({ opened_before: "2026-10-01T12:00:00Z" }).openedBefore).toBe("2026-10-01T12:00:00Z")
	})

	it("reads on its chip as the window, or the bound it has", () => {
		const format = (iso: string) => iso.slice(5, 10)
		expect(openedLabel(ALL, format)).toBe("09-01 – 10-01")
		expect(openedLabel({ ...ALL, openedBefore: null }, format)).toBe("since 09-01")
		expect(openedLabel({ ...ALL, openedFrom: null }, format)).toBe("before 10-01")
		expect(openedLabel(EMPTY_ALERTS_FILTERS, format)).toBe("")
	})
})

describe("calendar days", () => {
	it("accepts real days only", () => {
		expect(isDay("2026-10-13")).toBe(true)
		expect(isDay("2028-02-29")).toBe(true)
		for (const value of ["2026-02-29", "2026-13-01", "2026-1-1", "13/10/2026", "", null])
			expect(isDay(value)).toBe(false)
	})

	it("round-trips through the date picker's timestamps, in local time", () => {
		expect(timestampToDay(dayToTimestamp("2026-03-29"))).toBe("2026-03-29")
		expect(timestampToDay(new Date(2026, 9, 13, 23, 30).getTime())).toBe("2026-10-13")
	})
})
