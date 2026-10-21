import { describe, expect, it } from "vitest"
import source from "../CustomerDetailsTabs.vue?raw"

/**
 * `?tab=<name>` opens a customer's sub-tab only when the name is in `CUSTOMER_SUB_TABS`, so a
 * tab missing from that set can't be linked to: it opens on Info instead ("Portal
 * Notifications" was left out when it was added). Every tab pane of the Customer tab is in it.
 */
function customerPanes(): string[] {
	const customer = source.slice(source.indexOf('name="Customer"'), source.indexOf('name="Agents"'))
	return [...customer.matchAll(/<n-tab-pane[^>]*?\sname="([^"]+)"/g)].map(m => m[1] ?? "")
}

function subTabSet(): string[] {
	const body = source.match(/const CUSTOMER_SUB_TABS = new Set\(\[([\s\S]*?)\]\)/)?.[1] ?? ""
	return [...body.matchAll(/"([^"]+)"/g)].map(m => m[1] ?? "")
}

describe("customer sub-tabs reachable by ?tab=", () => {
	it("finds the panes and the set", () => {
		expect(customerPanes()).toContain("Info")
		expect(subTabSet()).toContain("Info")
	})

	it("lists every pane of the Customer tab, and nothing else", () => {
		expect([...subTabSet()].sort()).toEqual([...customerPanes()].sort())
	})
})
