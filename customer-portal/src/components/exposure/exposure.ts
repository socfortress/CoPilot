import type { LocationQuery, LocationQueryRaw, LocationQueryValue, RouteLocationRaw } from "vue-router"
import type { FilterStripOption } from "@/components/agents/AgentDetails/FilterStrip.vue"
import type { ExposureSeverity, SeverityCount } from "@/types/exposure"
import { severityDot } from "@/components/agents/AgentDetails/agentFindings"
import { severityText } from "@/components/sla/sla"
import { i18nGlobal } from "@/lang"

/**
 * Pure presentation logic of the Exposure page (#1289): what lives in the URL, how figures
 * read, and where a click takes the user. Kept out of the components so it is testable.
 *
 * In the URL: `?tab=vulnerabilities|compliance` (the first left out), and for the
 * vulnerabilities `?severity=High&q=openssl&page=2`. Every change replaces the entry, like
 * every filter in the portal.
 */

export type ExposureTab = "vulnerabilities" | "compliance"
export const EXPOSURE_TABS: ExposureTab[] = ["vulnerabilities", "compliance"]
export const SEVERITIES: ExposureSeverity[] = ["Critical", "High", "Medium", "Low"]
export const PAGE_SIZE = 25

type QueryValue = LocationQueryValue | LocationQueryValue[] | undefined

function single(value: QueryValue): string | null {
	const raw = Array.isArray(value) ? value[0] : value
	return typeof raw === "string" && raw.trim() ? raw.trim() : null
}

export function tabFromQuery(query: LocationQuery): ExposureTab {
	const tab = single(query.tab)
	return tab === "compliance" ? "compliance" : "vulnerabilities"
}

export interface VulnerabilityState {
	severity: ExposureSeverity | null
	search: string
	page: number
}

export function vulnerabilityStateFromQuery(query: LocationQuery): VulnerabilityState {
	const severity = single(query.severity)
	const page = Number.parseInt(single(query.page) ?? "", 10)
	return {
		severity: SEVERITIES.includes(severity as ExposureSeverity) ? (severity as ExposureSeverity) : null,
		search: (single(query.q) ?? "").slice(0, 100),
		page: Number.isInteger(page) && page >= 1 ? page : 1
	}
}

/**
 * `query` with the tab written (the first one left out) and, given a `state`, the
 * vulnerabilities' filters rewritten (defaults left out). Every other key is kept, the
 * filters too when no `state` is given: switching tabs keeps them for the way back.
 */
export function withExposureQuery(
	query: LocationQuery,
	tab: ExposureTab,
	state: VulnerabilityState | null = null
): LocationQueryRaw {
	const { tab: _tab, ...rest } = query
	const next: LocationQueryRaw = { ...rest }
	if (tab !== "vulnerabilities") next.tab = tab
	if (state) {
		delete next.severity
		delete next.q
		delete next.page
		if (state.severity) next.severity = state.severity
		if (state.search.trim()) next.q = state.search.trim()
		if (state.page > 1) next.page = String(state.page)
	}
	return next
}

/** The severity strip: every level and "All", each a count of distinct CVEs, and the filter. */
export function severityOptions(
	counts: SeverityCount[],
	loading = false
): FilterStripOption<ExposureSeverity | "All">[] {
	const by = Object.fromEntries(counts.map(item => [item.severity, item.cves]))
	const all = counts.reduce((sum, item) => sum + item.cves, 0)
	return [
		{ value: "All", label: i18nGlobal.t("exposure.vulnerabilities.all"), count: loading ? 0 : all, dot: "bg-muted" },
		...SEVERITIES.map(level => ({
			value: level,
			label: severityText(level),
			count: loading ? 0 : (by[level] ?? 0),
			dot: severityDot(level)
		}))
	]
}

/** EPSS as people read it: the probability of exploitation in the next 30 days, in percent. */
export function formatEpss(epss: string | null | undefined): string {
	if (epss === null || epss === undefined || epss === "") return "—"
	const value = Number(epss)
	if (!Number.isFinite(value)) return "—"
	const percent = value * 100
	return percent > 0 && percent < 0.1 ? "<0.1%" : `${percent.toFixed(1)}%`
}

/** "5 CVEs on 3 agents · 12 findings", in the singular where it is one. */
export function totalsLine(totals: { cves: number; hosts: number; findings: number }): string {
	const t = i18nGlobal.t
	return t("exposure.vulnerabilities.totals", {
		cves: countLabel("cves", totals.cves),
		agents: countLabel("agents", totals.hosts),
		findings: countLabel("findings", totals.findings)
	})
}

/** "3 agents", "1 policy": a count in words, in the current language. */
export function countLabel(noun: "cves" | "agents" | "findings" | "policies", count: number): string {
	const key = `exposure.counts.${noun}` as const
	return i18nGlobal.t(key, { count: count.toLocaleString() }, count)
}

/** The agent's page, opened on the tab a row came from, filtered to what was clicked. */
export function agentLink(
	agentId: string,
	target: { tab: "vulnerabilities"; search: string } | { tab: "sca"; policy: string }
): RouteLocationRaw {
	const query: LocationQueryRaw = { tab: target.tab }
	if (target.tab === "vulnerabilities") query.search = target.search
	else query.policy = target.policy
	return { name: "AgentDetails", params: { id: agentId }, query }
}

/** Only web links are followed; anything else Wazuh lists is shown as text. */
export function isWebLink(reference: string): boolean {
	return /^https?:\/\/\S+$/i.test(reference)
}

/** A file name for the CSV: what it is, the filter, and when. */
export function exportFilename(state: { severity: ExposureSeverity | null; search: string }, now = new Date()): string {
	const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-")
	const parts = [
		"vulnerabilities",
		state.severity?.toLowerCase(),
		state.search.trim().replace(/[^\w.-]+/g, "_") || null
	]
	return `${parts.filter(Boolean).join("-")}-${stamp}.csv`
}

export { severityText }

/** The average score of a policy as a meter level, the agent tab's scale. */
export { formatCvss, SCORE_COLORS, scoreLevel, severityClasses } from "@/components/agents/AgentDetails/agentFindings"
