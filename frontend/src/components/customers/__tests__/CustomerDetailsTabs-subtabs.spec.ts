import { describe, expect, it } from "vitest"
import source from "../CustomerDetailsTabs.vue?raw"
import { SECTION_IDS } from "../sections/sections"

/**
 * Every section of the navigation (#1325) has exactly one pane, and every pane is a section: a
 * section without a pane opens on nothing, and a pane without a section can't be reached (nor
 * linked to by `?tab=`). Each pane's three mentions of its id agree.
 */
function panes(): { opened: string; shown: string; bound: string }[] {
	const pattern =
		/<section\s+v-if="wasOpened\('([^']+)'\)[^"]*"\s+v-show="current === '([^']+)'"\s+v-bind="pane\('([^']+)'/g
	return [...source.matchAll(pattern)].map(match => ({
		opened: match[1] ?? "",
		shown: match[2] ?? "",
		bound: match[3] ?? ""
	}))
}

describe("customer sections and their panes", () => {
	it("finds the panes", () => {
		expect(panes().map(pane => pane.opened)).toContain("Info")
	})

	it("has one pane per section, and nothing else", () => {
		expect(panes().map(pane => pane.opened).sort()).toEqual([...SECTION_IDS].sort())
	})

	it("names the same section three times in each pane", () => {
		for (const pane of panes()) {
			expect(pane.shown).toBe(pane.opened)
			expect(pane.bound).toBe(pane.opened)
		}
	})
})
