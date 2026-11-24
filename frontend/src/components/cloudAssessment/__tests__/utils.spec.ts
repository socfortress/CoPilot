import type { CloudAccount, CloudScanCounts } from "@/types/cloud-assessment"
import { describe, expect, it } from "vitest"
import {
	canScan,
	durationText,
	expiryState,
	frameworkOrder,
	naturalCompare,
	passRate,
	prowlerRoleTemplateUrl,
	safeLink,
	scanOutcome,
	scheduleText,
	severitySegments
} from "../utils"

function counts(overrides: Partial<CloudScanCounts> = {}): CloudScanCounts {
	return {
		total: 0,
		passed: 0,
		failed: 0,
		manual: 0,
		muted: 0,
		failed_critical: 0,
		failed_high: 0,
		failed_medium: 0,
		failed_low: 0,
		failed_informational: 0,
		failed_unknown: 0,
		new_failed: 0,
		resolved_failed: 0,
		...overrides
	}
}

function account(overrides: Partial<CloudAccount> = {}): CloudAccount {
	return {
		id: 1,
		customer_code: "ACME",
		name: "Production",
		provider: "aws",
		auth_method: "access_keys",
		config: {},
		cloud_account: "123456789012",
		external_id: null,
		secret_configured: true,
		secret_hint: "…WXYZ",
		secret_expires_at: null,
		secret_expires_in_days: null,
		enabled: true,
		schedule: "off",
		schedule_hour: null,
		schedule_weekday: null,
		next_scheduled_at: null,
		last_connection_test_at: null,
		last_connection_ok: null,
		last_connection_error: null,
		last_connection_message: null,
		created_by: null,
		created_at: null,
		updated_by: null,
		updated_at: null,
		last_scan: null,
		last_completed_scan: null,
		...overrides
	}
}

describe("severitySegments", () => {
	it("gives each severity with failures its share, worst first, and leaves out the rest", () => {
		const segments = severitySegments(counts({ failed_critical: 2, failed_medium: 6, failed_low: 2 }))
		expect(segments).toEqual([
			{ severity: "critical", count: 2, percent: 20 },
			{ severity: "medium", count: 6, percent: 60 },
			{ severity: "low", count: 2, percent: 20 }
		])
	})

	it("is empty with no failure", () => {
		expect(severitySegments(counts({ passed: 40 }))).toEqual([])
	})
})

describe("passRate", () => {
	it("counts passed among the checks with an outcome, never manual or muted", () => {
		expect(passRate(counts({ passed: 3, failed: 1, manual: 50, muted: 50 }))).toBe(75)
	})

	it("is null, not 0, when nothing passed or failed", () => {
		expect(passRate(counts({ manual: 4 }))).toBeNull()
	})
})

describe("scheduleText", () => {
	it("reads each schedule in UTC", () => {
		expect(scheduleText({ schedule: "off", schedule_hour: null, schedule_weekday: null })).toBe("Not scheduled")
		expect(scheduleText({ schedule: "daily", schedule_hour: 2, schedule_weekday: null })).toBe("Daily at 02:00 UTC")
		expect(scheduleText({ schedule: "weekly", schedule_hour: 23, schedule_weekday: 6 })).toBe("Weekly, Sunday at 23:00 UTC")
		expect(scheduleText({ schedule: "weekly", schedule_hour: 0, schedule_weekday: 0 })).toBe("Weekly, Monday at 00:00 UTC")
	})
})

describe("expiryState", () => {
	const at = "2026-12-31T23:59:59Z"

	it("flags an expired credential and one within 30 days", () => {
		expect(expiryState({ secret_expires_at: at, secret_expires_in_days: -1 })).toBe("expired")
		expect(expiryState({ secret_expires_at: at, secret_expires_in_days: 0 })).toBe("soon")
		expect(expiryState({ secret_expires_at: at, secret_expires_in_days: 30 })).toBe("soon")
		expect(expiryState({ secret_expires_at: at, secret_expires_in_days: 31 })).toBe("ok")
	})

	it("says nothing about a credential without an expiry", () => {
		expect(expiryState({ secret_expires_at: null, secret_expires_in_days: null })).toBe("unknown")
	})
})

describe("durationText", () => {
	it("reads seconds, minutes and hours", () => {
		expect(durationText(45)).toBe("45 s")
		expect(durationText(125)).toBe("2 min 5 s")
		expect(durationText(3725)).toBe("1 h 2 min")
		expect(durationText(null)).toBeNull()
		expect(durationText(-3)).toBeNull()
	})
})

describe("scanOutcome", () => {
	it("says what a scan found and what changed since the scan before", () => {
		const found = counts({ total: 445, failed: 61, new_failed: 5, resolved_failed: 2 })
		expect(scanOutcome({ status: "completed", counts: found, error_message: null, previous_scan_id: 10 })).toBe(
			"61 failed of 445 · 5 new, 2 resolved"
		)
		expect(scanOutcome({ status: "completed", counts: counts({ total: 12 }), error_message: null, previous_scan_id: 3 })).toBe(
			"All 12 passed · 0 new, 0 resolved"
		)
	})

	it("never reads a first scan's zero new and resolved as \"no change\"", () => {
		expect(scanOutcome({ status: "completed", counts: counts({ total: 445, failed: 61 }), error_message: null, previous_scan_id: null })).toBe(
			"61 failed of 445 · first scan"
		)
	})

	it("says why a scan failed, or where it is", () => {
		expect(scanOutcome({ status: "failed", counts: counts(), error_message: "The credentials were refused.", previous_scan_id: null })).toBe(
			"The credentials were refused."
		)
		expect(scanOutcome({ status: "ingesting", counts: counts(), error_message: null, previous_scan_id: null })).toBe("Storing results")
	})
})

describe("naturalCompare and frameworkOrder", () => {
	it("read numbers in ids as numbers", () => {
		expect(["1.10", "1.2", "1.1", "2.1", "1.11"].sort(naturalCompare)).toEqual(["1.1", "1.2", "1.10", "1.11", "2.1"])
	})

	it("list each framework's newest version first", () => {
		const fw = (key: string, family: string | null, version: string | null) => ({
			key,
			framework: family,
			version,
			name: null,
			description: null,
			requirements_total: 1,
			passed: 0,
			failed: 0,
			manual: 0,
			not_assessed: 1
		})
		const sorted = [fw("CIS-1.4", "CIS", "1.4"), fw("ISO27001-2013", "ISO27001", "2013"), fw("CIS-5.0", "CIS", "5.0"), fw("CIS-1.10", "CIS", "1.10")]
			.sort(frameworkOrder)
			.map(item => item.key)
		expect(sorted).toEqual(["CIS-5.0", "CIS-1.10", "CIS-1.4", "ISO27001-2013"])
	})
})

describe("safeLink", () => {
	it("keeps http(s) links only", () => {
		expect(safeLink("https://docs.aws.amazon.com/iam/")).toBe("https://docs.aws.amazon.com/iam/")
		expect(safeLink("http://example.com/a")).toBe("http://example.com/a")
	})

	it("turns anything else into no link at all", () => {
		expect(safeLink("javascript:alert(document.cookie)")).toBeNull()
		expect(safeLink("JaVaScRiPt:alert(1)")).toBeNull()
		expect(safeLink("data:text/html,<script>alert(1)</script>")).toBeNull()
		expect(safeLink("vbscript:msgbox(1)")).toBeNull()
		expect(safeLink("/relative/path")).toBeNull()
		expect(safeLink("not a url")).toBeNull()
		expect(safeLink("")).toBeNull()
		expect(safeLink(null)).toBeNull()
	})
})

describe("prowlerRoleTemplateUrl", () => {
	it("points at the template of the Prowler that runs, else master", () => {
		expect(prowlerRoleTemplateUrl("5.13.1")).toBe(
			"https://github.com/prowler-cloud/prowler/blob/5.13.1/permissions/templates/cloudformation/prowler-scan-role.yml"
		)
		expect(prowlerRoleTemplateUrl(null)).toContain("/blob/master/")
		expect(prowlerRoleTemplateUrl("5.13.1/../../x")).toContain("/blob/master/")
	})
})

describe("canScan", () => {
	it("needs an enabled account with a credential and no scan under way", () => {
		expect(canScan(account())).toBe(true)
		expect(canScan(account({ enabled: false }))).toBe(false)
		expect(canScan(account({ secret_configured: false }))).toBe(false)
		const running = {
			id: 3,
			status: "running" as const,
			trigger_type: "manual" as const,
			queued_at: null,
			completed_at: null,
			counts: null,
			error_code: null,
			previous_scan_id: null
		}
		expect(canScan(account({ last_scan: running }))).toBe(false)
		expect(canScan(account({ last_scan: { ...running, status: "failed" } }))).toBe(true)
	})

	it("lets a role assumed with CoPilot's host identity scan without a stored credential", () => {
		expect(canScan(account({ auth_method: "role", secret_configured: false }))).toBe(true)
	})
})
