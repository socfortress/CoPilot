import type { SocRequest } from "@/types/soc-requests"
import { describe, expect, it } from "vitest"
import { answeredText, openCount, questionTarget, targetLabel } from "../customerQuestions"
import { question } from "./fixtures"

/** Customer questions (#1305), in words. */
describe("customer questions", () => {
	it("are filed on their case, else on the alert the customer kept them on", () => {
		expect(questionTarget(question(1, { case_id: 4, origin_alert_id: 9 }))).toEqual({ entity: "case", id: 4 })
		expect(questionTarget(question(2, { alert_id: 9 }))).toEqual({ entity: "alert", id: 9 })
		expect(questionTarget(question(3))).toBeNull()
		expect(targetLabel(question(1, { case_id: 4, title: "Brute force" }))).toBe("Case #4 · Brute force")
		expect(targetLabel(question(2, { alert_id: 9 }))).toBe("Alert #9")
		expect(targetLabel(question(3))).toBe("Removed")
	})

	it("count the open ones on one case or alert", () => {
		const list: SocRequest[] = [
			question(1, { case_id: 4 }),
			question(2, { case_id: 4 }),
			question(3, { case_id: 4, status: "answered" }),
			question(4, { alert_id: 4 }),
			question(5, { case_id: 7, origin_alert_id: 4 })
		]
		expect(openCount(list, "case", 4)).toBe(2)
		expect(openCount(list, "alert", 4)).toBe(1)
		expect(openCount(list, "case", 99)).toBe(0)
	})

	it("say how they were answered", () => {
		expect(answeredText(question(1))).toBe("")
		expect(answeredText(question(1, { status: "answered", answered_by: "ana", answered_via: "comment" }))).toBe(
			"Answered in a comment by ana"
		)
		expect(answeredText(question(1, { status: "answered", answered_via: "manual" }))).toBe("Marked answered")
	})
})
