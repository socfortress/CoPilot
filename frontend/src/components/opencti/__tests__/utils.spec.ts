import { describe, expect, it } from "vitest"
import { markingType, scoreColor, scoreTagType } from "../utils"

describe("score and marking helpers", () => {
	it.each([
		[null, undefined, "default"],
		[40, undefined, "default"],
		[50, "warning", "warning"],
		[75, "danger", "error"],
		[100, "danger", "error"]
	] as const)("score %s", (score, badge, tag) => {
		expect(scoreColor(score)).toBe(badge)
		expect(scoreTagType(score)).toBe(tag)
	})

	it.each([
		["TLP:RED", "error"],
		["TLP:AMBER+STRICT", "warning"],
		["tlp:green", "success"],
		["TLP:CLEAR", "default"],
		["PAP:WHITE", "default"]
	] as const)("marking %s", (marking, type) => {
		expect(markingType(marking)).toBe(type)
	})
})
