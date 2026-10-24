import type { AuditEntry } from "@/types/audit"
import { describe, expect, it } from "vitest"
import {
	actorLabel,
	changeLabel,
	EMPTY_STATE,
	exportFilename,
	hasFilters,
	retentionText,
	stateFromQuery,
	stateToQuery,
	targetEntity,
	targetLabel,
	targetRoute,
	withFilter,
	withState
} from "../auditLog"

function entry(extra: Partial<AuditEntry> = {}): AuditEntry {
	return {
		id: 1,
		timestamp: "2026-10-01T12:00:00Z",
		action: "alert.status_change",
		label: "Alert status changed",
		category: "alerts",
		actor: { kind: "member", username: "jane" },
		customer_code: "ACME",
		target: { type: "alert", id: "7", label: null },
		from_value: "OPEN",
		to_value: "CLOSED",
		result: "success",
		source_ip: "203.0.113.7",
		...extra
	}
}

/** The Audit Log page's URL state and wording (#1298). */
describe("the URL state", () => {
	it("reads every filter, dropping what it can't read", () => {
		expect(stateFromQuery({ category: "cases", user: "12", from: "2026-10-01", to: "2026-10-07", customer: "ACME", page: "3" })).toEqual({
			category: "cases",
			userId: 12,
			from: "2026-10-01",
			to: "2026-10-07",
			customer: "ACME",
			page: 3
		})
		expect(stateFromQuery({ category: "connectors", user: "x", from: "2026-02-30", to: "yesterday", page: "0" })).toEqual(EMPTY_STATE)
		expect(stateFromQuery({ user: "-4", page: "1e3" })).toEqual(EMPTY_STATE)
	})

	it("puts days the wrong way round in order", () => {
		const state = stateFromQuery({ from: "2026-10-07", to: "2026-10-01" })
		expect([state.from, state.to]).toEqual(["2026-10-01", "2026-10-07"])
	})

	it("writes the state with its defaults left out, keeping other keys", () => {
		expect(withState({ other: "x", page: "4", user: "1" }, { ...EMPTY_STATE, category: "account" })).toEqual({
			other: "x",
			category: "account"
		})
		expect(withState({}, { ...EMPTY_STATE, userId: 3, page: 2 })).toEqual({ user: "3", page: "2" })
	})

	it("goes back to the first page when a filter changes", () => {
		expect(withFilter({ ...EMPTY_STATE, page: 5 }, { category: "reports" })).toEqual({ ...EMPTY_STATE, category: "reports" })
		expect(hasFilters(EMPTY_STATE)).toBe(false)
		expect(hasFilters({ ...EMPTY_STATE, page: 3 })).toBe(false)
		expect(hasFilters({ ...EMPTY_STATE, customer: "ACME" })).toBe(true)
	})

	it("asks the API for whole local days, the end exclusive", () => {
		const query = stateToQuery({ ...EMPTY_STATE, from: "2026-10-01", to: "2026-10-07", category: "users", userId: 4, page: 2 })
		expect(query.since).toBe(new Date(2026, 9, 1).toISOString())
		expect(query.until).toBe(new Date(2026, 9, 8).toISOString())
		expect(query).toMatchObject({ category: "users", userId: 4, page: 2, pageSize: 25 })
		expect(stateToQuery(EMPTY_STATE)).toMatchObject({ since: null, until: null, category: null, userId: null })
	})
})

describe("an entry, in words", () => {
	it("names the customer's own users and never the SOC's", () => {
		expect(actorLabel({ kind: "member", username: "jane" })).toBe("jane")
		expect(actorLabel({ kind: "soc", username: null })).toBe("SOC")
		expect(actorLabel({ kind: "other", username: null })).toBe("Another portal user")
		expect(actorLabel({ kind: "unknown", username: null })).toBe("Unknown")
	})

	it("names the target, and says how it opens", () => {
		expect(targetLabel({ type: "alert", id: "7", label: null })).toBe("Alert #7")
		expect(targetLabel({ type: "case", id: "3", label: "Ransomware" })).toBe("Case #3 · Ransomware")
		expect(targetLabel({ type: "user", id: "jane", label: "jane" })).toBe("jane")
		expect(targetLabel(null)).toBe("")
		// An alert or a case opens in its modal: the page sees which, never a route.
		expect(targetEntity(entry())).toEqual({ type: "alert", id: 7 })
		expect(targetEntity(entry({ target: { type: "case", id: "3", label: null } }))).toEqual({ type: "case", id: 3 })
		expect(targetEntity(entry({ target: { type: "alert", id: "../x", label: null } }))).toBeNull()
		expect(targetEntity(entry({ target: { type: "user", id: "jane", label: "jane" } }))).toBeNull()
		expect(targetRoute(entry())).toBeNull()
		expect(targetRoute(entry({ target: { type: "case", id: "3", label: null } }))).toBeNull()
		// A report has no modal: it leads to the reports list while it still exists.
		expect(targetRoute(entry({ action: "report.download", target: { type: "report", id: "9", label: "Q3" } }))).toEqual({
			name: "ReportsList"
		})
		expect(targetEntity(entry({ action: "report.download", target: { type: "report", id: "9", label: "Q3" } }))).toBeNull()
		expect(targetRoute(entry({ action: "report.delete", target: { type: "report", id: "9", label: "Q3" } }))).toBeNull()
		expect(targetRoute(entry({ target: { type: "user", id: "jane", label: "jane" } }))).toBeNull()
	})

	it("says a status change in the portal's words", () => {
		expect(changeLabel(entry())).toBe("Open → Closed")
		expect(changeLabel(entry({ to_value: "PENDING_CUSTOMER" }))).toBe("Open → Waiting on you")
		expect(changeLabel(entry({ from_value: null, to_value: null }))).toBe("")
	})

	it("says how long the log goes back", () => {
		expect(retentionText(90)).toBe("Kept for 90 days: older entries are removed.")
		expect(retentionText(1)).toBe("Kept for 1 day: older entries are removed.")
		expect(retentionText(0)).toMatch(/as long as your SOC keeps/)
	})

	it("names the export by the time it was taken", () => {
		expect(exportFilename(new Date(2026, 9, 3, 7, 5))).toBe("audit-log-20261003-0705.csv")
	})
})
