import { describe, expect, it } from "vitest"
import getItems from "../items"

const keys = (features?: Parameters<typeof getItems>[0]) => getItems(features).map(item => item.key)

/** The menu offers the opt-in pages only to users whose customer has them on (#1187, #1284). */
describe("navbar items", () => {
	it("leaves the opt-in pages out by default", () => {
		expect(keys()).not.toContain("Activity")
		expect(keys()).not.toContain("Sla")
	})

	it("offers Activity only when its switch is on, keyed by its route name", () => {
		expect(keys({ activity: true })).toContain("Activity")
		expect(keys({ activity: true })).not.toContain("Sla")
		expect(keys({ sla: true })).not.toContain("Activity")
	})

	it("puts Activity before Service Levels, after every other page", () => {
		const all = keys({ activity: true, sla: true })
		expect(all.slice(-2)).toEqual(["Activity", "Sla"])
		expect(all[0]).toBe("Overview")
	})
})
