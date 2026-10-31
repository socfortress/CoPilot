import { describe, expect, it } from "vitest"
import { checkedSummary, describePart, formProblem, PROBLEMS, reviewTurns } from "../portalChat"

const ON = { enabled: true, logSearch: false, daily: 200, perUser: 50 }

describe("the portal chat form's rules", () => {
	it("needs AI reports and a daily limit to turn the chat on", () => {
		expect(formProblem(ON, true)).toBeNull()
		expect(formProblem(ON, false)).toBe(PROBLEMS.needsAiReports)
		expect(formProblem({ ...ON, daily: null, perUser: null }, true)).toBe(PROBLEMS.needsDaily)
		// Off, nothing is needed.
		expect(formProblem({ ...ON, enabled: false, daily: null, perUser: null }, false)).toBeNull()
	})

	it("keeps the limits whole, in range, and the per-user one under the customer's", () => {
		expect(formProblem({ ...ON, daily: 0 }, true)).toBe(PROBLEMS.range)
		expect(formProblem({ ...ON, daily: 100_001 }, true)).toBe(PROBLEMS.range)
		expect(formProblem({ ...ON, perUser: 1.5 }, true)).toBe(PROBLEMS.range)
		expect(formProblem({ ...ON, perUser: 201 }, true)).toBe(PROBLEMS.perUserOverDaily)
		expect(formProblem({ ...ON, enabled: false, daily: null }, true)).toBe(PROBLEMS.perUserWithoutDaily)
		expect(formProblem({ ...ON, perUser: null }, true)).toBeNull()
	})
})

describe("the review's transcript lines", () => {
	it("summarises what Talon checked", () => {
		expect(
			checkedSummary({
				items: [
					{ kind: "alert", count: 1 },
					{ kind: "event_search", count: 2 },
					{ kind: "intel", type: "ip", count: 1 },
					{ kind: "something_new", count: 3 }
				]
			})
		).toBe("Checked: the alert, 2 event searches, a threat-intel lookup (ip), 3 something_new")
		expect(checkedSummary({ items: [] })).toBeNull()
		expect(checkedSummary("nonsense")).toBeNull()
	})

	it("describes each part as plain text, and skips what it doesn't know", () => {
		expect(describePart({ type: "text", text: "<img src=x onerror=alert(1)>" })).toEqual({
			kind: "text",
			text: "<img src=x onerror=alert(1)>"
		})
		expect(describePart({ type: "data-soc-draft", data: { id: "6f1c", status: "submitted" } })).toEqual({
			kind: "draft",
			text: "Drafted a question for the SOC (6f1c): submitted"
		})
		expect(describePart({ type: "data-ai-analysis-offer", data: { alert_id: 4127 } })?.text).toBe(
			"Offered an AI analysis of alert 4127"
		)
		expect(describePart({ type: "tool-portal_get_alert", state: "output-available" })?.text).toBe(
			"portal_get_alert (output-available)"
		)
		expect(describePart({ type: "reasoning", text: "secret" })).toBeNull()
		expect(describePart({ type: "text", text: "   " })).toBeNull()
		expect(describePart(null)).toBeNull()
	})

	it("turns messages into turns with who, status and feedback", () => {
		const turns = reviewTurns([
			{ id: "r1-user", role: "user", parts: [{ type: "text", text: "What happened?" }] },
			{
				id: "r1-assistant",
				role: "assistant",
				parts: [
					{ type: "data-checked", data: { items: [{ kind: "alert", count: 1 }] } },
					{ type: "text", text: "The alert on HOST-A…" }
				],
				metadata: { status: "failed", error_text: "Talon request failed", feedback: "down" } as never
			}
		])
		expect(turns.map(t => t.who)).toEqual(["customer", "talon"])
		expect(turns[1]?.lines.map(l => l.kind)).toEqual(["checked", "text"])
		expect([turns[1]?.status, turns[1]?.errorText, turns[1]?.feedback]).toEqual([
			"failed",
			"Talon request failed",
			"down"
		])
	})
})
