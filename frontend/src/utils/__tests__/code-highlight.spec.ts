import { describe, expect, it } from "vitest"
import {
	DETECT_SAMPLE_CHARS,
	detectionSample,
	highlightable,
	MAX_HIGHLIGHT_CHARS,
	MAX_SHOWN_CHARS,
	shownCode
} from "../code-highlight"

describe("detectionSample", () => {
	it("hands detection all of a short code", () => {
		expect(detectionSample("$a = 1")).toBe("$a = 1")
	})

	it("hands detection only the start of a long one", () => {
		const line = "x".repeat(70_000)
		expect(detectionSample(line)).toHaveLength(DETECT_SAMPLE_CHARS)
	})
})

describe("highlightable", () => {
	it("highlights code up to the limit, and nothing larger", () => {
		expect(highlightable("x".repeat(MAX_HIGHLIGHT_CHARS))).toBe(true)
		expect(highlightable("x".repeat(MAX_HIGHLIGHT_CHARS + 1))).toBe(false)
	})
})

describe("shownCode", () => {
	it("shows all of code within the limit", () => {
		expect(shownCode("abc")).toEqual({ text: "abc", hidden: 0 })
	})

	it("shows the start of larger code, and says how much is left out", () => {
		const code = "y".repeat(MAX_SHOWN_CHARS + 500)
		const shown = shownCode(code)
		expect(shown.text).toHaveLength(MAX_SHOWN_CHARS)
		expect(shown.hidden).toBe(500)
	})

	it("shows everything once asked", () => {
		const code = "y".repeat(MAX_SHOWN_CHARS + 500)
		expect(shownCode(code, true)).toEqual({ text: code, hidden: 0 })
	})

	it("never cuts a character in half", () => {
		// An emoji is two UTF-16 units: one that straddles the limit is left out whole.
		const code = `${"z".repeat(MAX_SHOWN_CHARS - 1)}😀tail`
		const shown = shownCode(code)
		expect(shown.text).toBe("z".repeat(MAX_SHOWN_CHARS - 1))
		expect(shown.hidden).toBe(code.length - (MAX_SHOWN_CHARS - 1))
	})
})
