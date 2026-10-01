import type { SlaEntity, SlaOverview, SlaTarget } from "@/types/sla"
import { describe, expect, it } from "vitest"
import {
	buildKpis,
	formatDuration,
	formatRate,
	formatTarget,
	groupTargets,
	hasActivity,
	periodRange,
	rateDelta,
	rateTone
} from "../sla"

function entity(overrides: Partial<SlaEntity> = {}): SlaEntity {
	return {
		opened: 6,
		resolved: 1,
		acknowledge: { met: 5, breached: 1, rate: 83.3 },
		resolve: { met: 1, breached: 0, rate: 100 },
		time_to_acknowledge: 600,
		time_to_resolve: 10_800,
		...overrides
	}
}

function target(overrides: Partial<SlaTarget>): SlaTarget {
	return {
		entity: "alert",
		severity: "High",
		acknowledge_minutes: 60,
		resolve_minutes: 480,
		business_hours: false,
		opened: 0,
		acknowledge_rate: null,
		resolve_rate: null,
		time_to_resolve: null,
		...overrides
	}
}

const overview: SlaOverview = {
	enabled: true,
	customer_codes: ["ACME"],
	date_from: "2026-09-01T00:00:00",
	date_to: "2026-10-01T00:00:00",
	bucket: "day",
	tracking_since: null,
	alerts: entity(),
	cases: entity({ opened: 0, resolved: 0, acknowledge: { met: 0, breached: 0, rate: null }, time_to_acknowledge: null }),
	previous_alerts: entity({ acknowledge: { met: 9, breached: 1, rate: 90 } }),
	previous_cases: null,
	targets: [],
	trend: [],
	open_now: { alerts: 5, cases: 2, breached: 0, at_risk: 1, waiting_on_you: 2 }
}

describe("sLA page presentation (#1187)", () => {
	it("periods end now and reach back the preset's days", () => {
		const now = new Date("2026-10-02T12:00:00Z")
		const { from, to } = periodRange("7d", now)
		expect(to).toBe(now)
		expect(from.toISOString()).toBe("2026-09-25T12:00:00.000Z")
	})

	it("says durations the way a person would", () => {
		expect(formatDuration(null)).toBe("—")
		expect(formatDuration(42)).toBe("42s")
		expect(formatDuration(600)).toBe("10m")
		expect(formatDuration(3 * 3600 + 20 * 60)).toBe("3h 20m")
		expect(formatDuration(7200)).toBe("2h")
		expect(formatDuration(2 * 86_400 + 4 * 3600)).toBe("2d 4h")
	})

	it("shows no outcome as a dash, never as 0%", () => {
		expect(formatRate(null)).toBe("—")
		expect(formatRate(100)).toBe("100%")
		expect(formatRate(83.3)).toBe("83.3%")
		expect(rateTone(null)).toBe("neutral")
		expect([rateTone(99), rateTone(85), rateTone(50)]).toEqual(["success", "warning", "error"])
	})

	it("states targets in their natural unit, and a missing one as no target", () => {
		expect(formatTarget(15)).toBe("15 min")
		expect(formatTarget(90)).toBe("90 min")
		expect(formatTarget(480)).toBe("8 h")
		expect(formatTarget(4320)).toBe("3 d")
		expect(formatTarget(null)).toBe("No target")
	})

	it("compares with the previous period in points, only when both have an outcome", () => {
		expect(rateDelta(83.3, 90)).toEqual({ points: -6.7, direction: "down" })
		expect(rateDelta(95, 95)).toEqual({ points: 0, direction: "flat" })
		expect(rateDelta(95, null)).toEqual({ points: null, direction: "flat" })
	})

	it("builds the four headline figures with counts, medians and deltas", () => {
		const [alertAck, alertResolve, caseAck] = buildKpis(overview)
		expect(alertAck).toMatchObject({ title: "Alert response", rate: 83.3, met: 5, decided: 6, median: "10m" })
		expect(alertAck!.delta).toEqual({ points: -6.7, direction: "down" })
		expect(alertResolve).toMatchObject({ title: "Alert resolution", rate: 100, median: "3h" })
		expect(caseAck).toMatchObject({ rate: null, decided: 0, median: "—" })
		expect(caseAck!.delta.points).toBeNull()
	})

	it("knows when a period has nothing to show", () => {
		expect(hasActivity(overview)).toBe(true)
		expect(hasActivity({ ...overview, alerts: entity({ opened: 0, resolved: 0 }) })).toBe(false)
	})

	it("groups the promise by entity, alerts first, dropping an empty group", () => {
		const groups = groupTargets([target({ entity: "case", severity: "Critical" }), target({ severity: "Critical" })])
		expect(groups.map(group => group.title)).toEqual(["Alerts", "Cases"])
		expect(groupTargets([target({})]).map(group => group.entity)).toEqual(["alert"])
	})
})
