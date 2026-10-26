import { describe, expect, it } from "vitest"
import { filedOn, normalizeQuestion, QUESTION_MAX, questionLength, questionProblem, targetOptions } from "../askSoc"
import { request } from "./fixtures"

/** What the "Ask the SOC" form checks before sending (#1305): the backend's own rules. */
describe("a question for the SOC", () => {
	it("is sent trimmed, with Windows line ends folded", () => {
		expect(normalizeQuestion("  Line one\r\nline two \n")).toBe("Line one\nline two")
	})

	it("must say something", () => {
		expect(questionProblem("")).toBe("Write your question for the SOC")
		expect(questionProblem(" \n\t ")).toBe("Write your question for the SOC")
		expect(questionProblem("Is this ours?")).toBeNull()
	})

	it("is counted in characters, as the backend counts them", () => {
		// One emoji is two UTF-16 units but one character.
		expect(questionLength("🙂")).toBe(1)
		expect(questionProblem("🙂".repeat(QUESTION_MAX))).toBeNull()
		expect(questionProblem("a".repeat(QUESTION_MAX + 1))).toBe(`Keep the question under ${QUESTION_MAX} characters`)
		// Surrounding blanks are trimmed before counting.
		expect(questionProblem(` ${"a".repeat(QUESTION_MAX)} `)).toBeNull()
	})

	it("keeps tabs and newlines, refuses other controls and hidden formatting characters", () => {
		expect(questionProblem("a\tb\nc")).toBeNull()
		for (const hex of ["0000", "0007", "000D", "001B", "007F", "200B", "200D", "202E", "2066", "FEFF", "061C"]) {
			expect(questionProblem(`pay ${String.fromCodePoint(Number.parseInt(hex, 16))}here`), `U+${hex}`).toBe(
				"The question contains characters that cannot be sent"
			)
		}
		expect(questionProblem("café, 日本語, ü")).toBeNull()
	})
})

describe("where a question on an alert goes", () => {
	it("offers the alert's open case when it has one, else a new case, and always the alert", () => {
		expect(targetOptions(12).map(o => [o.value, o.label])).toEqual([
			["case", "Add to case #12"],
			["alert", "On this alert only"]
		])
		expect(targetOptions(null).map(o => [o.value, o.label])).toEqual([
			["case", "Open a case from this alert"],
			["alert", "On this alert only"]
		])
	})

	it("says where a listed question was filed when it isn't the page it's on", () => {
		expect(filedOn(request(1, { case_id: 4, origin_alert_id: 9 }), "alert")).toBe("On case #4")
		expect(filedOn(request(1, { alert_id: 9 }), "alert")).toBeNull()
		expect(filedOn(request(1, { case_id: 4, origin_alert_id: 9 }), "case")).toBe("Asked from alert #9")
		expect(filedOn(request(1, { case_id: 4 }), "case")).toBeNull()
	})
})
