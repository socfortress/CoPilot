import type { PolicyMatrix } from "@/types/soc-management"
import { describe, expect, it } from "vitest"
import {
	buildPolicyPayload,
	cellError,
	computeDelta,
	computePointDelta,
	formatCount,
	formatDuration,
	formatOverdue,
	formatRate,
	formatTarget,
	isPolicyDirty,
	isValidRange,
	joinMinutes,
	parseUtc,
	presetRange,
	rateTone,
	splitMinutes,
	toEditableCells
} from "../utils"

describe("formatDuration (twin of the backend's formatting.duration)", () => {
	it.each([
		[null, "—"],
		[42, "42s"],
		[60, "1m"],
		[3599, "59m"],
		[3600, "1h"],
		[4800, "1h 20m"],
		[3900, "1h 05m"],
		[86400, "1d"],
		[2 * 86400 + 4 * 3600, "2d 4h"]
	])("%s s → %s", (seconds, text) => {
		expect(formatDuration(seconds)).toBe(text)
	})

	it("reads magnitudes, so a negative 'time left' formats like a positive one", () => {
		expect(formatDuration(-90)).toBe("1m")
	})
})

describe("rates and counts", () => {
	it("never renders a missing rate as 0%", () => {
		expect(formatRate(null)).toBe("—")
		expect(formatRate(96.84)).toBe("96.8%")
		expect(formatRate(0)).toBe("0.0%")
	})

	it("tones a rate against the SLA objective", () => {
		expect(rateTone(99)).toBe("good")
		expect(rateTone(95)).toBe("good")
		expect(rateTone(90)).toBe("warn")
		expect(rateTone(42)).toBe("bad")
		expect(rateTone(null)).toBe("neutral")
	})

	it("counts are exact below ten thousand and compact above", () => {
		expect(formatCount(1284)).toBe("1,284")
		expect(formatCount(12_900)).toBe("12.9K")
		expect(formatCount(null)).toBe("—")
	})

	it("formats targets and overdue clocks", () => {
		expect(formatTarget(null)).toBe("no target")
		expect(formatTarget(90)).toBe("1h 30m")
		expect(formatOverdue(7500)).toBe("2h 05m late")
		expect(formatOverdue(-2100)).toBe("35m left")
	})
})

describe("deltas vs the previous period", () => {
	it("tones by which direction is good news", () => {
		expect(computeDelta(120, 100, "up")).toEqual({ label: "+20%", direction: "up", tone: "good" })
		expect(computeDelta(120, 100, "down")).toEqual({ label: "+20%", direction: "up", tone: "bad" })
		expect(computeDelta(80, 100)).toEqual({ label: "−20%", direction: "down", tone: "neutral" })
	})

	it("handles flat, new and unknown", () => {
		expect(computeDelta(100, 100)?.direction).toBe("flat")
		expect(computeDelta(5, 0)?.label).toBe("new")
		expect(computeDelta(0, 0)).toBeNull()
		expect(computeDelta(null, 3)).toBeNull()
	})

	it("compares rates in percentage points", () => {
		expect(computePointDelta(97, 95)).toEqual({ label: "+2.0 pts", direction: "up", tone: "good" })
		expect(computePointDelta(90, 95)?.tone).toBe("bad")
		expect(computePointDelta(null, 95)).toBeNull()
	})
})

describe("periods", () => {
	it("builds a rolling window ending on the next minute", () => {
		const range = presetRange("7d", new Date("2026-09-30T10:15:42Z"))
		expect(range.to.toISOString()).toBe("2026-09-30T10:16:00.000Z")
		expect(range.from.toISOString()).toBe("2026-09-23T10:16:00.000Z")
	})

	it("rejects backwards and over-long ranges, as the backend does", () => {
		const day = new Date("2026-09-01T00:00:00Z")
		expect(isValidRange({ from: day, to: new Date("2026-09-02T00:00:00Z") })).toBe(true)
		expect(isValidRange({ from: day, to: day })).toBe(false)
		expect(isValidRange({ from: day, to: new Date("2027-09-10T00:00:00Z") })).toBe(false)
		expect(isValidRange(null)).toBe(false)
	})

	it("parses the backend's naive timestamps as UTC", () => {
		expect(parseUtc("2026-09-01T08:00:00")?.toISOString()).toBe("2026-09-01T08:00:00.000Z")
		expect(parseUtc("2026-09-01T08:00:00+02:00")?.toISOString()).toBe("2026-09-01T06:00:00.000Z")
		expect(parseUtc(null)).toBeNull()
	})
})

describe("policy editor helpers", () => {
	const matrix: PolicyMatrix = {
		customer_code: "ACME",
		cells: [
			{ entity: "alert", severity: "High", ack_minutes: 10, resolve_minutes: 60, source: "customer" },
			{ entity: "alert", severity: "Low", ack_minutes: 480, resolve_minutes: 4320, source: "global" },
			{ entity: "case", severity: "Low", ack_minutes: 1440, resolve_minutes: 20160, source: "default" }
		]
	}

	it("marks a customer's own cells as stored and the rest as inherited", () => {
		const cells = toEditableCells(matrix)
		expect(cells.map(c => c.inherit)).toEqual([false, true, true])
		expect(cells[1].inheritedFrom).toBe("global")
	})

	it("global cells inherit only from the built-in defaults", () => {
		const cells = toEditableCells({ ...matrix, customer_code: null })
		expect(cells.map(c => c.inherit)).toEqual([true, false, true])
	})

	it("sends inheriting cells without targets", () => {
		const payload = buildPolicyPayload(toEditableCells(matrix), "ACME", true)
		expect(payload.customer_code).toBe("ACME")
		expect(payload.apply_to_open).toBe(true)
		expect(payload.cells[1]).toEqual({
			entity: "alert",
			severity: "Low",
			inherit: true,
			ack_minutes: null,
			resolve_minutes: null
		})
		expect(payload.cells[0].ack_minutes).toBe(10)
	})

	it("is dirty only when what would be stored changes", () => {
		const original = toEditableCells(matrix)
		const same = toEditableCells(matrix)
		expect(isPolicyDirty(same, original)).toBe(false)
		same[1].ack_minutes = 1 // an inheriting cell's shown value is not stored
		expect(isPolicyDirty(same, original)).toBe(false)
		same[0].ack_minutes = 15
		expect(isPolicyDirty(same, original)).toBe(true)
		const overridden = toEditableCells(matrix)
		overridden[2].inherit = false
		expect(isPolicyDirty(overridden, original)).toBe(true)
	})

	it("flags the cells the backend would reject", () => {
		const base = { entity: "alert" as const, severity: "High" as const, inherit: false }
		expect(cellError({ ...base, ack_minutes: 600, resolve_minutes: 60 })).toMatch(/longer than the resolution/)
		expect(cellError({ ...base, ack_minutes: 0, resolve_minutes: 60 })).toMatch(/above zero/)
		expect(cellError({ ...base, ack_minutes: 1.5, resolve_minutes: 60 })).toMatch(/whole minutes/)
		expect(cellError({ ...base, ack_minutes: 600_000, resolve_minutes: null })).toMatch(/one year/)
		expect(cellError({ ...base, ack_minutes: null, resolve_minutes: null })).toBeNull()
		expect(cellError({ ...base, inherit: true, ack_minutes: 600, resolve_minutes: 60 })).toBeNull()
	})

	it("splits minutes into the largest exact unit and joins them back", () => {
		expect(splitMinutes(90)).toEqual({ value: 90, unit: "m" })
		expect(splitMinutes(120)).toEqual({ value: 2, unit: "h" })
		expect(splitMinutes(4320)).toEqual({ value: 3, unit: "d" })
		expect(splitMinutes(null)).toEqual({ value: null, unit: "h" })
		expect(joinMinutes(3, "d")).toBe(4320)
		expect(joinMinutes(1.5, "h")).toBe(90)
		expect(joinMinutes(null, "m")).toBeNull()
	})
})
