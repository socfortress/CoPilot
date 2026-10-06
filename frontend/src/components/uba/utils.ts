import type { UbaAgentsSummary, UbaFailureReason, UbaIdentitySummary } from "@/types/uba"

/** What to do about an upstream failure (the proxy returns a `reason`, never a 401/403). */
export function reasonHint(reason: UbaFailureReason | string | null | undefined): string | null {
	switch (reason) {
		case "not_configured":
			return "Set the SOCFortress UBA connector's URL and API key under Connectors."
		case "unreachable":
			return "CoPilot can't reach the UBA API. Check the connector URL and that UBA's API is published where CoPilot's backend can reach it."
		case "key_rejected":
			return "UBA rejected the API key. Create one with `uba-admin api-keys create --name copilot --scope write` and update the connector."
		case "insufficient_scope":
			return "The UBA API key can only read. Suppressions and verdicts need a key with scope write."
		case "not_found":
			return "UBA has no such item for this customer (or the API key isn't allowed to see this customer)."
		default:
			return null
	}
}

export type RiskTone = "error" | "warning" | "info" | "neutral"

/**
 * Risk bands follow UBA's alerting, relative to the customer's alert threshold (100 by default):
 * at the threshold an alert opens, half as much again is high, under 30% of it is background.
 */
export function riskTone(risk: number, threshold = 100): RiskTone {
	if (risk >= threshold * 1.5) return "error"
	if (risk >= threshold) return "warning"
	if (risk >= threshold * 0.3) return "info"
	return "neutral"
}

export function riskTagType(risk: number, threshold = 100): "error" | "warning" | "info" | "default" {
	const tone = riskTone(risk, threshold)
	return tone === "neutral" ? "default" : tone
}

/** Full class names, written out so Tailwind finds them. */
export const RISK_TEXT_CLASS: Record<RiskTone, string> = {
	error: "text-error",
	warning: "text-warning",
	info: "text-info",
	neutral: "text-secondary"
}

export const RISK_BG_CLASS: Record<RiskTone, string> = {
	error: "bg-error",
	warning: "bg-warning",
	info: "bg-info",
	neutral: "bg-[var(--fg-tertiary-color)]"
}

/** An entity type's icon (carbon), for headers and lists. */
export function entityTypeIcon(type: string | null | undefined): string {
	switch (entityTypeLabel(type)) {
		case "host":
			return "carbon:laptop"
		case "address":
			return "carbon:network-3"
		case "tenant":
			return "carbon:enterprise"
		default:
			return "carbon:user"
	}
}

export function riskLabel(risk: number): string {
	return risk >= 10 ? risk.toFixed(0) : risk.toFixed(1)
}

export const ENTITY_TYPE_LABEL: Record<string, string> = {
	actor: "user",
	target: "user",
	host: "host",
	src_ip: "address",
	tenant: "tenant"
}

export function entityTypeLabel(type: string | null | undefined): string {
	return (type && ENTITY_TYPE_LABEL[type]) || type || "entity"
}

export function formatLag(seconds: number | null | undefined): string {
	if (seconds == null) return "unknown"
	if (seconds < 90) return `${Math.round(seconds)} s`
	if (seconds < 5400) return `${Math.round(seconds / 60)} min`
	return `${Math.round(seconds / 3600)} h`
}

export const FALSE_POSITIVE_REASONS = [
	{ label: "Expected activity", value: "EXPECTED_ACTIVITY" },
	{ label: "Known application", value: "KNOWN_APPLICATION" },
	{ label: "Authorized user", value: "AUTHORIZED_USER" },
	{ label: "Rule too sensitive", value: "RULE_TOO_SENSITIVE" },
	{ label: "Other", value: "OTHER" }
]

/** Where an identity attribute or membership came from, in words. */
export const IDENTITY_SOURCE_LABELS: Record<string, string> = {
	entra: "Entra ID (directory sync)",
	entra_audit: "Entra audit log",
	windows_audit: "Windows security log",
	manual: "set manually",
	ldap: "Active Directory (LDAP)",
	observed: "seen in events"
}

export function identitySourceLabel(source: string | null | undefined): string {
	if (!source) return "unknown source"
	return IDENTITY_SOURCE_LABELS[source] ?? source
}

/**
 * A privileged reason as stored by UBA (``<source>:<role|group>:<name>`` or ``observed:privileged_hint``)
 * in words: what the identity holds and how UBA knows.
 */
export function privilegedReasonLabel(reason: string): { what: string; how: string } {
	if (reason === "observed:privileged_hint") return { what: "Acted with admin rights", how: "seen in events" }
	const [source, kind, ...rest] = reason.split(":")
	const name = rest.join(":")
	if (!name) return { what: reason, how: "" }
	const holds = kind === "role" ? "role" : "group"
	const where = source.startsWith("windows") ? "Windows" : source.startsWith("entra") ? "Entra" : ""
	const how = source === "entra" ? "directory sync" : source.endsWith("_audit") ? "seen granted in the audit log" : identitySourceLabel(source)
	return { what: name, how: `${[where, holds].filter(Boolean).join(" ")}, ${how}` }
}

/** "WS02 (since <time>), DC01 and 3 more": the computers not reporting, for the page's warning. */
export function silentComputers(agents: UbaAgentsSummary, formatTime: (iso: string) => string): string {
	const names = agents.not_reporting_hosts.map(h =>
		h.last_keepalive ? `${h.name} (since ${formatTime(h.last_keepalive)})` : h.name
	)
	const more = agents.not_reporting - names.length
	return names.join(", ") + (more > 0 ? ` and ${more} more` : "")
}

/** Tooltip of the "computers" badge. Retired agents (silent over 30 days) are not counted. */
export function agentsSummaryTitle(agents: UbaAgentsSummary): string {
	const lines = [`${agents.reporting} of ${agents.total - agents.retired} computers with a Wazuh agent are reporting`]
	if (agents.retired) lines.push(`${agents.retired} silent for over 30 days (not counted)`)
	if (agents.never_connected) lines.push(`${agents.never_connected} enrolled but never connected`)
	return lines.join("\n")
}

/** An identity's name: its display name, else its strongest alias without the type. */
export function identityLabel(i: UbaIdentitySummary): string {
	if (i.display_name) return i.display_name
	const alias = i.aliases[0]
	return alias ? alias.slice(alias.indexOf(":") + 1) : i.id
}

/** "human · admin · 3 findings in 14 days · upn:jdoe@…, sid:S-1-5-…" */
export function identityDetails(i: UbaIdentitySummary): string {
	const parts = [i.kind && i.kind !== "unknown" ? i.kind : null, i.privileged ? "admin" : null]
	parts.push(`${i.findings} finding${i.findings === 1 ? "" : "s"} in 14 days`)
	const aliases = i.aliases.slice(0, 2).join(", ")
	if (aliases) parts.push(aliases)
	return parts.filter(Boolean).join(" · ")
}
