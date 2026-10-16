import type { EventSearchResult } from "@/types/siem"
import { describe, expect, it } from "vitest"
import {
	cellText,
	columnSource,
	columnValue,
	DEFAULT_COLUMNS,
	eventsFilename,
	eventsToCsv,
	eventTime,
	getNestedValue,
	resolveColumns
} from "../eventColumns"

const EVENT = {
	timestamp: "2026-10-01T10:00:00",
	agent: { name: "web-01" },
	rule: { level: 10, description: "Login failed" },
	tags: ["a", "b"],
	data: { src: { ip: "203.0.113.7" } }
} as unknown as EventSearchResult

/** What the table shows and the CSV holds: one definition for both (#1258). */
describe("event columns", () => {
	it("chooses the user's columns, else the source's, else the default layout", () => {
		const user = [{ key: "agent.name", label: "Agent" }]
		const source = [{ key: "rule.level", label: "Level" }]
		expect(resolveColumns(user, source, "timestamp").map(c => c.key)).toEqual(["agent.name"])
		expect(resolveColumns(null, source, "timestamp").map(c => c.key)).toEqual(["rule.level"])
		expect(resolveColumns([], [], "timestamp")).toBe(DEFAULT_COLUMNS)
	})

	it("marks the time columns: the source's time field or any timestamp", () => {
		const columns = resolveColumns(
			[
				{ key: "ts", label: "When" },
				{ key: "data.timestamp_utc", label: "" },
				{ key: "agent.name", label: "Agent" }
			],
			null,
			"ts"
		)
		expect(columns.map(c => [c.label, c.time])).toEqual([
			["When", true],
			["data.timestamp_utc", true],
			["Agent", false]
		])
	})

	it("reads nested fields, and the default columns from either shape of an event", () => {
		expect(getNestedValue(EVENT, "data.src.ip")).toBe("203.0.113.7")
		expect(getNestedValue(EVENT, "data.nope.x")).toBeUndefined()
		const [time, level, source, rule] = DEFAULT_COLUMNS.map(c => columnValue(c, EVENT, "timestamp"))
		expect([time, level, source, rule]).toEqual(["2026-10-01T10:00:00", 10, "web-01", "Login failed"])
		const flat = { agent_name: "db-01", rule_level: 3, rule_description: "ok" } as unknown as EventSearchResult
		expect(DEFAULT_COLUMNS.slice(1).map(c => columnValue(c, flat, null))).toEqual([3, "db-01", "ok"])
	})

	it("finds an event's time by the source's field first, then any timestamp", () => {
		expect(eventTime({ "@timestamp": "x", "ts": "y" } as unknown as EventSearchResult, "ts")).toBe("y")
		expect(eventTime({ "@timestamp": "x" } as unknown as EventSearchResult, "ts")).toBe("x")
	})

	it("writes values as text: lists joined, objects as JSON, nothing empty", () => {
		expect([cellText(["a", null, 2]), cellText({ a: 1 }), cellText(null), cellText(0)]).toEqual(["a, , 2", '{"a":1}', "", "0"])
	})
})

describe("events as CSV", () => {
	it("one header per column and one row per event, times in ISO 8601 UTC", () => {
		const columns = resolveColumns(
			[
				{ key: "timestamp", label: "When" },
				{ key: "agent.name", label: "Agent" },
				{ key: "tags", label: "Tags" }
			],
			null,
			"timestamp"
		)
		const { headers, rows } = eventsToCsv(columns, [EVENT], "timestamp")
		expect(headers).toEqual(["When", "Agent", "Tags"])
		// An offset-less time is UTC, as everywhere else on the page.
		expect(rows).toEqual([["2026-10-01T10:00:00.000Z", "web-01", "a, b"]])
	})

	it("keeps a time it cannot read as it came", () => {
		const columns = resolveColumns([{ key: "timestamp", label: "When" }], null, "timestamp")
		const odd = { timestamp: "yesterday-ish" } as unknown as EventSearchResult
		expect(eventsToCsv(columns, [odd], "timestamp").rows).toEqual([["yesterday-ish"]])
	})

	it("names the file after the source and the time", () => {
		expect(eventsFilename("Office 365 / Audit", new Date(Date.UTC(2026, 9, 15, 9, 5, 0)))).toBe(
			"events-Office_365_Audit-2026-10-15-09-05-00.csv"
		)
	})

	it("names the field a column reads: its own, or the one behind a default column", () => {
		expect(DEFAULT_COLUMNS.map(column => columnSource(column, "@timestamp"))).toEqual([
			"@timestamp",
			"rule_level",
			"agent_name",
			"rule_description"
		])
		expect(columnSource(DEFAULT_COLUMNS[0]!, null)).toBe("timestamp")
		expect(columnSource(resolveColumns([{ key: "data.win.user", label: "User" }], null, null)[0]!, null)).toBe("data.win.user")
	})
})
