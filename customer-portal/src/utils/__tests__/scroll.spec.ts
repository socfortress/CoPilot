import { describe, expect, it } from "vitest"
import { startsAtTop } from "../scroll"

describe("startsAtTop (#1273)", () => {
	it("starts a new page at the top", () => {
		expect(startsAtTop({ path: "/alerts" }, { path: "/overview" })).toBe(true)
	})

	it("keeps the place when only the query changes: a period, a filter, a tab", () => {
		expect(startsAtTop({ path: "/overview" }, { path: "/overview" })).toBe(false)
	})
})
