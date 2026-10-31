import { describe, expect, it } from "vitest"
import getItems from "../items"

const keys = (features?: Parameters<typeof getItems>[0]) => getItems(features).map(item => item.key)

/** The menu offers the opt-in pages only to users whose customer has them on (#1187, #1284, #1289). */
describe("navbar items", () => {
	it("leaves the opt-in pages out by default", () => {
		expect(keys()).not.toContain("Activity")
		expect(keys()).not.toContain("Exposure")
		expect(keys()).not.toContain("Sla")
	})

	it("offers Activity only when its switch is on, keyed by its route name", () => {
		expect(keys({ activity: true })).toContain("Activity")
		expect(keys({ activity: true })).not.toContain("Sla")
		expect(keys({ sla: true })).not.toContain("Activity")
	})

	it("offers Exposure only when its switch is on, keyed by its route name", () => {
		expect(keys({ exposure: true })).toContain("Exposure")
		expect(keys({ exposure: true })).not.toContain("Activity")
		expect(keys({ sla: true, activity: true })).not.toContain("Exposure")
	})

	it("offers Ask Talon only when its availability says so (talon-analyst D97)", () => {
		expect(keys()).not.toContain("TalonChat")
		expect(keys({ talonChat: true })).toContain("TalonChat")
		expect(keys({ exposure: true, activity: true, sla: true })).not.toContain("TalonChat")
	})

	it("puts Exposure, Activity and Service Levels last, in that order", () => {
		const all = keys({ exposure: true, activity: true, sla: true, talonChat: true })
		expect(all.slice(-4)).toEqual(["TalonChat", "Exposure", "Activity", "Sla"])
		expect(all[0]).toBe("Overview")
		expect(keys({ activity: true, sla: true }).slice(-2)).toEqual(["Activity", "Sla"])
	})
})
