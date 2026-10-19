import { describe, expect, it } from "vitest"
import { investigationStatusMeta, STALE_INVESTIGATION_MS, utcMillis } from "../aiInvestigation"

const NOW = Date.parse("2026-10-17T12:00:00Z")
const startedAgo = (ms: number) => new Date(NOW - ms).toISOString().replace("Z", "")

describe("aI investigation status, in words (#1273)", () => {
	it("names every status the analyst pipeline reports, with its colour", () => {
		const recent = startedAgo(60_000)
		expect(
			["pending", "running", "completed", "failed"].map(status => {
				const { label, type, active } = investigationStatusMeta(status, recent, NOW)
				return [label, type, active]
			})
		).toEqual([
			["Queued", "info", true],
			["Analysing", "info", true],
			["Completed", "success", false],
			["Failed", "error", false]
		])
	})

	it("calls a job queued or running past the backend's wait stalled, and only those", () => {
		const old = startedAgo(STALE_INVESTIGATION_MS)
		expect(investigationStatusMeta("running", old, NOW)).toEqual({
			label: "Stalled",
			type: "warning",
			active: false,
			stalled: true
		})
		expect(investigationStatusMeta("pending", old, NOW).stalled).toBe(true)
		expect(investigationStatusMeta("running", startedAgo(STALE_INVESTIGATION_MS - 1_000), NOW).stalled).toBe(false)
		expect(investigationStatusMeta("completed", old, NOW).label).toBe("Completed")
	})

	it("shows a status it does not know as it came, never blank", () => {
		expect(investigationStatusMeta("cancelled", startedAgo(0), NOW)).toMatchObject({
			label: "Cancelled",
			type: "default"
		})
		expect(investigationStatusMeta("", startedAgo(0), NOW).label).toBe("Unknown")
	})

	it("reads a stored time as UTC, and one with an offset as such", () => {
		expect(utcMillis("2026-10-17T10:00:00")).toBe(Date.parse("2026-10-17T10:00:00Z"))
		expect(utcMillis("2026-10-17T12:00:00+02:00")).toBe(Date.parse("2026-10-17T10:00:00Z"))
	})
})
