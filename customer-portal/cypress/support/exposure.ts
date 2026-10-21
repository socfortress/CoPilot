import type { PortalSeed } from "./e2e"

/**
 * What Wazuh would answer for the Exposure page (#1289), shaped as the backend answers it.
 * The e2e backend has no Wazuh, so `exposure.cy.ts` serves these at the network layer; the
 * switch, the menu entry and the page's "not published" answer come from the real backend.
 * The aggregation itself is the backend's own test (tests/e2e/customer_portal_exposure_*).
 */

const SEVERITIES = ["Critical", "High", "Medium", "Low"] as const

function cve(n: number) {
	const severity = n < 2 ? "Critical" : n < 7 ? "High" : n < 27 ? "Medium" : "Low"
	return {
		cve_id: `CVE-2026-${String(2000 + n).padStart(5, "0")}`,
		severity,
		cvss: severity === "Critical" ? 9.8 : severity === "High" ? 8.1 : severity === "Medium" ? 5.5 : 2.1,
		epss: n === 0 ? "0.97412" : "0.0123",
		hosts: n === 0 ? 2 : 1,
		packages: [`package-${n}`],
		first_detected: "2026-09-01T10:00:00Z",
		published: "2026-08-01T00:00:00Z"
	}
}

/** 2 Critical, 5 High, 20 Medium, 3 Low: 30 CVEs, more than a page of 25. */
export const CVES = Array.from({ length: 30 }, (_, n) => cve(n))

export function vulnerabilitiesPage(seed: PortalSeed, query: { severity?: string; page?: string }) {
	const rows = query.severity ? CVES.filter(row => row.severity === query.severity) : CVES
	const page = Number(query.page ?? 1)
	return {
		success: true,
		message: "ok",
		enabled: true,
		customer_codes: [seed.customers.a],
		agents_in_scope: seed.agents_a.total,
		severities: SEVERITIES.map(severity => {
			const count = CVES.filter(row => row.severity === severity).length
			return { severity, cves: count, hosts: 1, findings: count }
		}),
		totals: { cves: rows.length, hosts: 2, findings: rows.length + 1 },
		cves: rows.slice((page - 1) * 25, page * 25),
		total_cves: rows.length,
		page,
		page_size: 25,
		truncated: false,
		error: null
	}
}

export function cveDetail(seed: PortalSeed) {
	return {
		success: true,
		message: "ok",
		...CVES[0],
		description: "A flaw in package-0 lets an attacker run code.",
		references: [`https://nvd.nist.gov/vuln/detail/${CVES[0].cve_id}`],
		agents: [
			{
				agent_id: seed.agent_a0.agent_id,
				hostname: seed.agent_a0.hostname,
				customer_code: seed.customers.a,
				package: "package-0",
				version: "1.0.0",
				detected: "2026-09-01T10:00:00Z"
			}
		],
		truncated: false,
		error: null
	}
}

export const POLICY_ID = "cis_ubuntu22-04"

export function compliance(seed: PortalSeed) {
	return {
		success: true,
		message: "ok",
		enabled: true,
		customer_codes: [seed.customers.a],
		agents_in_scope: seed.agents_a.total,
		agents_assessed: 2,
		unavailable_agents: 1,
		average_score: 62,
		passed: 138,
		failed: 74,
		weak_score: 50,
		policies: [
			{
				policy_id: POLICY_ID,
				name: "CIS Ubuntu Linux 22.04 LTS Benchmark",
				description: null,
				agents: 2,
				average_score: 41,
				min_score: 25,
				passed: 98,
				failed: 72,
				invalid: 30,
				agents_below: 1
			},
			{
				policy_id: "sca_unix_audit",
				name: "System audit for Unix based systems",
				description: null,
				agents: 1,
				average_score: 95,
				min_score: 95,
				passed: 40,
				failed: 2,
				invalid: 0,
				agents_below: 0
			}
		],
		read_at: "2026-10-20T08:00:00Z",
		error: null
	}
}

export function policyAgents(seed: PortalSeed) {
	return {
		success: true,
		message: "ok",
		policy_id: POLICY_ID,
		name: "CIS Ubuntu Linux 22.04 LTS Benchmark",
		agents: [
			{
				agent_id: seed.agent_a0.agent_id,
				hostname: seed.agent_a0.hostname,
				customer_code: seed.customers.a,
				score: 25,
				passed: 40,
				failed: 60,
				invalid: 10,
				end_scan: "2026-10-20T07:00:00Z"
			}
		],
		error: null
	}
}
