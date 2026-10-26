import type { AgentScaCheck, AgentScaPolicy, AgentVulnerability, VulnerabilitySeverity } from "@/types/agents"
import { i18nGlobal } from "@/lang"

/**
 * What an agent's Vulnerabilities and SCA tabs show (#1256), as pure functions: filtering,
 * counting, ordering and the look of a severity or a result. The components only fetch
 * and render.
 */

export const SEVERITIES: VulnerabilitySeverity[] = ["Critical", "High", "Medium", "Low"]

/** Wazuh spells severities its own way at times ("CRITICAL", "critical"): read them as one. */
export function normalizeSeverity(severity: string | null | undefined): VulnerabilitySeverity | null {
	const value = (severity ?? "").trim().toLowerCase()
	return SEVERITIES.find(s => s.toLowerCase() === value) ?? null
}

export type SeverityCounts = Record<VulnerabilitySeverity | "All", number>

export function severityCounts(vulnerabilities: AgentVulnerability[]): SeverityCounts {
	const counts: SeverityCounts = { All: vulnerabilities.length, Critical: 0, High: 0, Medium: 0, Low: 0 }
	for (const v of vulnerabilities) {
		const severity = normalizeSeverity(v.severity)
		if (severity) counts[severity]++
	}
	return counts
}

function matches(needle: string, ...texts: (string | null | undefined)[]) {
	return !needle || texts.some(text => (text ?? "").toLowerCase().includes(needle))
}

/**
 * The vulnerabilities to list: of one severity (or all), matching the search on CVE, title
 * or package, worst first — by severity, then by CVSS score, then by CVE.
 */
export function filterVulnerabilities(
	vulnerabilities: AgentVulnerability[],
	{ severity, search }: { severity: VulnerabilitySeverity | "All"; search: string }
): AgentVulnerability[] {
	const needle = search.trim().toLowerCase()
	const rank = (v: AgentVulnerability) => {
		const index = SEVERITIES.indexOf(normalizeSeverity(v.severity) as VulnerabilitySeverity)
		return index === -1 ? SEVERITIES.length : index
	}
	return vulnerabilities
		.filter(
			v =>
				(severity === "All" || normalizeSeverity(v.severity) === severity) &&
				matches(needle, v.cve, v.title, v.name)
		)
		.sort(
			(a, b) =>
				rank(a) - rank(b) ||
				(b.cvss3_score ?? -1) - (a.cvss3_score ?? -1) ||
				(a.cve ?? "").localeCompare(b.cve ?? "")
		)
}

/**
 * A severity as the reader's language names it: a known one by its label, anything else Wazuh
 * sent as it came, and none as "unknown". "All" names the filter that shows every severity.
 */
export function severityLabel(severity: string | null | undefined): string {
	if (severity === "All") return i18nGlobal.t("agents.findings.severity.All")
	const known = normalizeSeverity(severity)
	if (known) return i18nGlobal.t(`agents.findings.severity.${known}`)
	return severity ?? i18nGlobal.t("agents.findings.severity.unknown")
}

/** Tailwind classes of a severity chip: a word, an outline, a tint — coloured by how bad it is. */
export function severityClasses(severity: string | null | undefined): string {
	switch (normalizeSeverity(severity)) {
		case "Critical":
			return "border-error/40 bg-error/10 text-error"
		case "High":
			return "border-warning/40 bg-warning/10 text-warning"
		case "Medium":
			return "border-info/40 bg-info/10 text-info"
		default:
			return "border-default text-secondary"
	}
}

/** A CVSS score as people write it: one decimal (9.8, 7.0), whatever float Wazuh stored. */
export function formatCvss(score: number | null | undefined): string {
	return score == null ? "—" : score.toFixed(1)
}

/** The dot beside a severity in the counts: the same hue as its chip. */
export function severityDot(severity: string | null | undefined): string {
	switch (normalizeSeverity(severity)) {
		case "Critical":
			return "bg-error"
		case "High":
			return "bg-warning"
		case "Medium":
			return "bg-info"
		default:
			return "bg-muted"
	}
}

export const SCA_RESULTS = ["failed", "passed", "not applicable"] as const

export type ScaResultFilter = (typeof SCA_RESULTS)[number] | "all"

export type ScaResultCounts = Record<ScaResultFilter, number>

export function scaResultCounts(checks: AgentScaCheck[]): ScaResultCounts {
	const counts: ScaResultCounts = { all: checks.length, failed: 0, passed: 0, "not applicable": 0 }
	for (const check of checks) {
		const result = check.result.toLowerCase() as ScaResultFilter
		if (result in counts && result !== "all") counts[result]++
	}
	return counts
}

/** The checks to list: of one result (or all), matching the search on title or id, failed first. */
export function filterScaChecks(
	checks: AgentScaCheck[],
	{ result, search }: { result: ScaResultFilter; search: string }
): AgentScaCheck[] {
	const needle = search.trim().toLowerCase()
	const order = (check: AgentScaCheck) => {
		const index = SCA_RESULTS.indexOf(check.result.toLowerCase() as (typeof SCA_RESULTS)[number])
		return index === -1 ? SCA_RESULTS.length : index
	}
	return checks
		.filter(c => (result === "all" || c.result.toLowerCase() === result) && matches(needle, c.title, String(c.id)))
		.sort((a, b) => order(a) - order(b) || a.id - b.id)
}

/** A check's result as the reader's language names it; one Wazuh reports otherwise is shown as it came. */
export function scaResultLabel(result: string): string {
	switch (result.toLowerCase()) {
		case "failed":
			return i18nGlobal.t("agents.findings.results.failed")
		case "passed":
			return i18nGlobal.t("agents.findings.results.passed")
		case "not applicable":
			return i18nGlobal.t("agents.findings.results.notApplicable")
		default:
			return result
	}
}

/** "1–25 of 300": the rows a page shows, out of how many. */
export function pageRangeLabel(from: number, to: number, total: number): string {
	return i18nGlobal.t("agents.findings.range", {
		from: from.toLocaleString(),
		to: to.toLocaleString(),
		total: total.toLocaleString()
	})
}

export function scaResultClasses(result: string): string {
	switch (result.toLowerCase()) {
		case "failed":
			return "border-error/40 bg-error/10 text-error"
		case "passed":
			return "border-success/40 bg-success/10 text-success"
		default:
			return "border-default text-secondary"
	}
}

/** A policy's score as a level: the colour of its meter. */
export function scoreLevel(score: number): "good" | "fair" | "poor" {
	if (score >= 80) return "good"
	if (score >= 50) return "fair"
	return "poor"
}

export const SCORE_COLORS: Record<ReturnType<typeof scoreLevel>, string> = {
	good: "bg-success",
	fair: "bg-warning",
	poor: "bg-error"
}

/** Worst policies first, so what needs attention is on top; a tie keeps the name order. */
export function sortScaPolicies(policies: AgentScaPolicy[]): AgentScaPolicy[] {
	return [...policies].sort(
		(a, b) => a.score - b.score || (a.name ?? a.policy_id).localeCompare(b.name ?? b.policy_id)
	)
}

/** A file name for an export: what it is, the agent, and when. */
export function exportFilename(kind: string, agentLabel: string, now = new Date()): string {
	const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-")
	const safe = agentLabel.replace(/[^\w.-]+/g, "_")
	return `${safe}-${kind}-${stamp}.csv`
}
