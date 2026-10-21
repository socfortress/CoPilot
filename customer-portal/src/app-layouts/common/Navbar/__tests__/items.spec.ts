import { describe, expect, it } from "vitest"
import getItems from "../items"

const keys = (features?: Parameters<typeof getItems>[0]) => getItems(features).map(item => item.key)

/** Pages a customer's SOC switches on appear in the menu only when on (#1187, #1289). */
describe("navbar items", () => {
	it("leaves out the pages that are off", () => {
		expect(keys()).not.toContain("Exposure")
		expect(keys()).not.toContain("Sla")
	})

	it("lists Exposure only when it is on, before Service Levels", () => {
		expect(keys({ exposure: true })).toContain("Exposure")
		expect(keys({ sla: true })).not.toContain("Exposure")
		const both = keys({ exposure: true, sla: true })
		expect(both.indexOf("Exposure")).toBeGreaterThan(-1)
		expect(both.indexOf("Exposure")).toBeLessThan(both.indexOf("Sla"))
	})
})
