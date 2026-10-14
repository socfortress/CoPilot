import type { AgentScaCheck, AgentScaPolicy, AgentVulnerability } from "@/types/agents"
import { describe, expect, it } from "vitest"
import {
	exportFilename,
	filterScaChecks,
	filterVulnerabilities,
	formatCvss,
	normalizeSeverity,
	scaResultCounts,
	scoreLevel,
	severityCounts,
	sortScaPolicies
} from "../agentFindings"

function vuln(cve: string, severity: string | null, cvss: number | null, name = "pkg"): AgentVulnerability {
	return {
		cve,
		severity,
		cvss3_score: cvss,
		name,
		title: `${cve} title`,
		version: "1.0",
		type: null,
		architecture: null,
		status: null,
		published: null,
		detection_time: null,
		external_references: null
	}
}

function check(id: number, result: string, title = `check ${id}`): AgentScaCheck {
	return {
		id,
		result,
		title,
		policy_id: "p",
		description: null,
		rationale: null,
		remediation: null,
		reason: null,
		command: null,
		condition: null,
		compliance: [],
		rules: []
	}
}

/** What an agent's Vulnerabilities and SCA tabs list, and how (#1256). */
describe("vulnerabilities", () => {
	const list = [
		vuln("CVE-3", "Medium", 5),
		vuln("CVE-1", "CRITICAL", 9.1),
		vuln("CVE-2", "critical", 9.8, "openssl"),
		vuln("CVE-4", "Low", null),
		vuln("CVE-5", null, 7)
	]

	it("reads Wazuh's spellings of a severity as one", () => {
		expect(["Critical", "CRITICAL", " critical "].map(normalizeSeverity)).toEqual([
			"Critical",
			"Critical",
			"Critical"
		])
		expect(normalizeSeverity("Untriaged")).toBeNull()
	})

	it("counts every severity, and an unknown one only in All", () => {
		expect(severityCounts(list)).toEqual({ All: 5, Critical: 2, High: 0, Medium: 1, Low: 1 })
	})

	it("lists the worst first: severity, then CVSS, unknown severities last", () => {
		const order = filterVulnerabilities(list, { severity: "All", search: "" }).map(v => v.cve)
		expect(order).toEqual(["CVE-2", "CVE-1", "CVE-3", "CVE-4", "CVE-5"])
	})

	it("filters by severity and searches CVE, title and package, case-insensitively", () => {
		expect(filterVulnerabilities(list, { severity: "Critical", search: "" })).toHaveLength(2)
		expect(filterVulnerabilities(list, { severity: "All", search: "OPENSSL" }).map(v => v.cve)).toEqual(["CVE-2"])
		expect(filterVulnerabilities(list, { severity: "All", search: "cve-3 title" }).map(v => v.cve)).toEqual([
			"CVE-3"
		])
		expect(filterVulnerabilities(list, { severity: "High", search: "" })).toEqual([])
	})

	it("writes a CVSS score with one decimal, whatever float was stored", () => {
		expect([9.700000000000001, 7, null].map(formatCvss)).toEqual(["9.7", "7.0", "—"])
	})
})

describe("sCA", () => {
	it("counts checks by result", () => {
		const checks = [check(1, "failed"), check(2, "passed"), check(3, "Failed"), check(4, "not applicable")]
		expect(scaResultCounts(checks)).toEqual({ all: 4, failed: 2, passed: 1, "not applicable": 1 })
	})

	it("lists failed checks first, then by id, and filters and searches them", () => {
		const checks = [
			check(3, "passed"),
			check(2, "failed", "Ensure AIDE"),
			check(1, "not applicable"),
			check(4, "failed")
		]
		expect(filterScaChecks(checks, { result: "all", search: "" }).map(c => c.id)).toEqual([2, 4, 3, 1])
		expect(filterScaChecks(checks, { result: "failed", search: "" }).map(c => c.id)).toEqual([2, 4])
		expect(filterScaChecks(checks, { result: "all", search: "aide" }).map(c => c.id)).toEqual([2])
		expect(filterScaChecks(checks, { result: "all", search: "4" }).map(c => c.id)).toEqual([4])
	})

	it("puts the worst policy first, and grades a score", () => {
		const policy = (policy_id: string, score: number) => ({ policy_id, score, name: policy_id }) as AgentScaPolicy
		expect(sortScaPolicies([policy("b", 90), policy("a", 40), policy("c", 40)]).map(p => p.policy_id)).toEqual([
			"a",
			"c",
			"b"
		])
		expect([95, 80, 79, 50, 49].map(scoreLevel)).toEqual(["good", "good", "fair", "fair", "poor"])
	})
})

describe("export file names", () => {
	it("say what, which agent and when, safe for any file system", () => {
		const at = new Date(Date.UTC(2026, 9, 14, 12, 30, 5))
		expect(exportFilename("vulnerabilities-high", "web 01/prod", at)).toBe(
			"web_01_prod-vulnerabilities-high-2026-10-14-12-30-05.csv"
		)
	})
})
