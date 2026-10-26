/**
 * The Ops tab's pure helpers: which action a status allows (talon-analyst's transitions), the mute
 * window (future, at most 90 days), the evidence as rows, labels, and what a failure shows.
 */
import { describe, expect, it } from "vitest"
import {
	canAcknowledge,
	canMute,
	canReopen,
	customerText,
	evidenceRows,
	isValidMuteUntil,
	jobLabel,
	kindLabel,
	OLD_TALON_OPS_TEXT,
	problemState,
	severityInfo,
	V2_OFF_TEXT
} from "../ops"

const DAY = 24 * 60 * 60 * 1000

describe("actions by status", () => {
	it.each([
		["open", true, true, false],
		["acknowledged", false, true, true],
		["muted", true, true, true],
		["resolved", false, false, false]
	] as const)("%s: acknowledge %s, mute %s, reopen %s", (status, ack, mute, reopen) => {
		expect(canAcknowledge(status)).toBe(ack)
		expect(canMute(status)).toBe(mute)
		expect(canReopen(status)).toBe(reopen)
	})
})

describe("the mute window", () => {
	const now = Date.UTC(2026, 9, 24, 12)
	it("is in the future and at most 90 days away", () => {
		expect(isValidMuteUntil(now + DAY, now)).toBe(true)
		expect(isValidMuteUntil(now + 90 * DAY, now)).toBe(true)
		expect(isValidMuteUntil(now + 90 * DAY + 1, now)).toBe(false)
		expect(isValidMuteUntil(now, now)).toBe(false)
		expect(isValidMuteUntil(now - 1, now)).toBe(false)
		expect(isValidMuteUntil(null, now)).toBe(false)
		expect(isValidMuteUntil(Number.NaN, now)).toBe(false)
	})
})

describe("evidence rows", () => {
	it("keeps the job's order, shows scalars and lists of scalars as text, and objects as JSON", () => {
		const rows = evidenceRows({
			agent_id: "017",
			critical_asset: false,
			wazuh_days_quiet: 5.1,
			velociraptor_id: null,
			conditions: ["wazuh_quiet", "velociraptor_quiet"],
			same_hour_last_4_weeks: [],
			nested: { a: 1 }
		})
		expect(rows.map(r => r.key)).toEqual([
			"agent_id",
			"critical_asset",
			"wazuh_days_quiet",
			"velociraptor_id",
			"conditions",
			"same_hour_last_4_weeks",
			"nested"
		])
		expect(rows.map(r => r.text)).toEqual([
			"017",
			"no",
			"5.1",
			"—",
			"wazuh_quiet, velociraptor_quiet",
			"none",
			null
		])
		expect(rows[6].json).toBe(JSON.stringify({ a: 1 }, null, 2))
	})

	it("is empty without evidence", () => {
		expect(evidenceRows(null)).toEqual([])
	})
})

describe("labels", () => {
	it("names jobs, kinds, customers and severities", () => {
		expect(jobLabel("quiet_endpoints")).toBe("Endpoints gone quiet")
		expect(jobLabel("quiet_endpoints", { quiet_endpoints: "Quiet agents" })).toBe("Quiet agents")
		expect(jobLabel("new_job")).toBe("new_job")
		expect(kindLabel("wazuh_quiet")).toBe("Wazuh quiet")
		expect(kindLabel("some_new_kind")).toBe("some new kind")
		expect(customerText(null)).toBe("Platform")
		expect(customerText("ACME")).toBe("ACME")
		expect(severityInfo("high")).toMatchObject({ label: "High", tag: "error" })
		expect(severityInfo("info")).toMatchObject({ label: "Info", tag: "default" })
	})
})

describe("problems", () => {
	it("tells v2 off and an old Talon apart from a failure", () => {
		expect(problemState({ status: 404, code: "v2_off", detail: "x" })).toMatchObject({
			kind: "v2_off",
			text: V2_OFF_TEXT
		})
		expect(problemState({ status: 404, code: "unsupported", detail: "x" })).toMatchObject({
			kind: "unsupported",
			text: OLD_TALON_OPS_TEXT
		})
		expect(problemState({ status: 502, code: "unavailable", detail: "Talon could not be reached" })).toMatchObject({
			kind: "error",
			text: "Talon could not be reached"
		})
		expect(problemState(null)).toBeNull()
	})
})
