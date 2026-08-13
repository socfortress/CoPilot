import { describe, expect, it } from "vitest"
import { entityCandidates, fuzzyFilter, toKeywords } from "../searchDialog.helpers"

interface Item {
	title: string
	tags: string[]
}

const ITEMS: Item[] = [
	{ title: "Detections Catalog", tags: ["rules", "wazuh"] },
	{ title: "SIEM Alerts", tags: ["siem", "wazuh"] },
	{ title: "Overview", tags: ["home", "dashboard"] },
	{ title: "Agents", tags: ["endpoints"] }
]

const KEYS: (keyof Item)[] = ["title", "tags"]

describe("fuzzyFilter", () => {
	it("returns the full list for a blank query", () => {
		expect(fuzzyFilter(ITEMS, "  ", KEYS)).toHaveLength(ITEMS.length)
	})

	it("finds items by a fuzzy title match", () => {
		const titles = fuzzyFilter(ITEMS, "catalog", KEYS).map(i => i.title)
		expect(titles).toContain("Detections Catalog")
	})

	it("finds items by a tag match", () => {
		const titles = fuzzyFilter(ITEMS, "dashboard", KEYS).map(i => i.title)
		expect(titles).toContain("Overview")
	})

	it("ranks the closest title first", () => {
		const results = fuzzyFilter(ITEMS, "agents", KEYS)
		expect(results[0].title).toBe("Agents")
	})

	it("returns nothing for a query that matches no item", () => {
		expect(fuzzyFilter(ITEMS, "zzzzz", KEYS)).toHaveLength(0)
	})
})

describe("toKeywords", () => {
	it("splits on whitespace and drops empties", () => {
		expect(toKeywords("  add   customer ")).toEqual(["add", "customer"])
	})

	it("returns an empty array for a blank query", () => {
		expect(toKeywords("   ")).toEqual([])
	})
})

describe("entityCandidates", () => {
	it("offers alert and case jumps for a numeric query", () => {
		const kinds = entityCandidates("123").map(c => c.kind)
		expect(kinds).toEqual(["alert", "case"])
	})

	it("strips a leading # from numeric ids", () => {
		const alert = entityCandidates("#42").find(c => c.kind === "alert")
		expect(alert?.target).toBe("42")
		expect(alert?.title).toBe("Go to Alert #42")
	})

	it("returns nothing for a non-numeric query", () => {
		expect(entityCandidates("crowd")).toEqual([])
	})

	it("returns nothing for a blank query", () => {
		expect(entityCandidates("   ")).toEqual([])
	})
})
