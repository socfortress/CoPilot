import type { AgentScaCheck, AgentScaPolicy, AgentVulnerability } from "../../src/types/agents"

/**
 * What Wazuh would answer for an agent's vulnerabilities and SCA (#1256). The e2e backend
 * runs without a Wazuh, so `agent-tabs.cy.ts` serves these at the network layer; the rest
 * of the page (the agent, its cases) comes from the real backend and database.
 */

function vulnerability(n: number, severity: string, cvss: number): AgentVulnerability {
	return {
		cve: `CVE-2026-${String(1000 + n).padStart(5, "0")}`,
		severity,
		title: `CVE-2026-${String(1000 + n).padStart(5, "0")} affects package-${n}`,
		name: `package-${n}`,
		version: `1.${n}.0`,
		type: "PACKAGE",
		architecture: "amd64",
		status: "VALID",
		cvss3_score: cvss,
		published: "2026-08-01T00:00:00Z",
		detection_time: "2026-09-01T10:00:00Z",
		external_references: [`https://nvd.nist.gov/vuln/detail/CVE-2026-${String(1000 + n).padStart(5, "0")}`]
	}
}

/** 2 Critical, 5 High, 20 Medium, 3 Low: 30 in all, more than a page of 25. */
export const VULNERABILITIES: AgentVulnerability[] = [
	...Array.from({ length: 2 }, (_, i) => vulnerability(i, "Critical", 9.8 - i / 10)),
	...Array.from({ length: 5 }, (_, i) => vulnerability(10 + i, "High", 8 - i / 10)),
	...Array.from({ length: 20 }, (_, i) => vulnerability(20 + i, "Medium", 5.5)),
	...Array.from({ length: 3 }, (_, i) => vulnerability(50 + i, "Low", 2.1))
]

export const SCA_POLICIES: AgentScaPolicy[] = [
	{
		policy_id: "cis_ubuntu22-04",
		name: "CIS Ubuntu Linux 22.04 LTS Benchmark",
		description: "CIS benchmark",
		references: null,
		pass: 98,
		fail: 72,
		invalid: 30,
		score: 57,
		total_checks: 200,
		start_scan: "2026-09-01T10:00:00Z",
		end_scan: "2026-09-01T10:02:00Z"
	},
	{
		policy_id: "sca_unix_audit",
		name: "System audit for Unix based systems",
		description: null,
		references: null,
		pass: 40,
		fail: 2,
		invalid: 0,
		score: 95,
		total_checks: 42,
		start_scan: null,
		end_scan: "2026-09-01T09:00:00Z"
	}
]

function check(id: number, result: string, title: string): AgentScaCheck {
	return {
		id,
		policy_id: "cis_ubuntu22-04",
		title,
		description: `${title}: description`,
		rationale: "Why it matters",
		remediation: "What to do",
		reason: "Reason not found",
		command: "Command not found",
		condition: "all",
		result,
		compliance: [{ key: "cis", value: "1.1.2" }],
		rules: []
	}
}

export const SCA_CHECKS: AgentScaCheck[] = [
	check(28500, "passed", "Ensure mounting of cramfs filesystems is disabled"),
	check(28501, "failed", "Ensure /tmp is a separate partition"),
	check(28502, "not applicable", "Ensure nodev option set on /tmp partition"),
	check(28503, "failed", "Ensure AIDE is installed")
]
