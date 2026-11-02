/**
 * The sections of a customer's page, grouped (#1325).
 *
 * A section's id is the name its tab had before the groups, so `?tab=<name>` links keep working,
 * and the old top-level tabs map onto a section (`tabToSection`). Pure: no Vue, no API.
 */
import type { CustomerSectionStatus } from "@/types/customers"

export const SECTION_IDS = [
	"Info",
	"Provision",
	"Security",
	"Agents",
	"Deploy Agent",
	"Healthcheck Wazuh",
	"Healthcheck Velociraptor",
	"Wazuh Worker",
	"3rd Party Integrations",
	"Network Connectors",
	"Event Sources",
	"WAF",
	"AI Triggers",
	"AI Automation",
	"Notification Workflows",
	"Notifications",
	"Reporting",
	"Portal Branding",
	"Portal Languages",
	"SLA",
	"Activity",
	"Exposure",
	"Audit Log",
	"AI Report",
	"Ask the SOC",
	"IOC Enrichment",
	"Portal Notifications"
] as const

export type SectionId = (typeof SECTION_IDS)[number]

export type GroupId = "overview" | "agents" | "data" | "automation" | "reports" | "portal"

/** What decides whether a section is shown at all. */
export type SectionRequirement = "admin" | "automation" | "wazuhWorker"

export interface SectionDef {
	id: SectionId
	/** What the navigation shows; the id is the old tab name. */
	label: string
	group: GroupId
	subgroup?: string
	/** Other words a search should find it by. */
	keywords?: string[]
	status?: keyof CustomerSectionStatus
	/** For a section that holds a list: the entry's name, singular and plural. */
	noun?: [string, string]
	requires?: SectionRequirement
}

export interface GroupDef {
	id: GroupId
	label: string
}

export const GROUPS: GroupDef[] = [
	{ id: "overview", label: "Overview" },
	{ id: "agents", label: "Agents" },
	{ id: "data", label: "Data sources" },
	{ id: "automation", label: "Automation & alerts" },
	{ id: "reports", label: "Reports" },
	{ id: "portal", label: "Customer Portal" }
]

export const SECTIONS: SectionDef[] = [
	{ id: "Info", label: "Info", group: "overview", keywords: ["contact", "address", "details", "edit", "delete"] },
	{ id: "Provision", label: "Provision", group: "overview", keywords: ["graylog", "grafana", "index", "meta"] },
	{
		id: "Security",
		label: "Security",
		group: "overview",
		keywords: ["users", "password", "2fa", "totp", "customer admin", "read-only", "portal users"],
		requires: "admin"
	},
	{ id: "Agents", label: "Agents list", group: "agents", keywords: ["endpoints", "hosts"] },
	{ id: "Deploy Agent", label: "Deploy Agent", group: "agents", keywords: ["install", "edr", "enroll"] },
	{ id: "Healthcheck Wazuh", label: "Healthcheck Wazuh", group: "agents", keywords: ["unhealthy", "last seen"] },
	{
		id: "Healthcheck Velociraptor",
		label: "Healthcheck Velociraptor",
		group: "agents",
		keywords: ["unhealthy", "last seen"]
	},
	{
		id: "Wazuh Worker",
		label: "Wazuh Worker",
		group: "agents",
		keywords: ["portainer", "stack"],
		requires: "wazuhWorker"
	},
	{
		id: "3rd Party Integrations",
		label: "3rd Party Integrations",
		group: "data",
		keywords: ["office365", "crowdstrike", "defender", "huntress", "mimecast"],
		status: "integrations",
		noun: ["integration", "integrations"]
	},
	{
		id: "Network Connectors",
		label: "Network Connectors",
		group: "data",
		keywords: ["firewall", "fortinet", "cato"],
		status: "network_connectors",
		noun: ["connector", "connectors"]
	},
	{
		id: "Event Sources",
		label: "Event Sources",
		group: "data",
		keywords: ["indices", "index pattern", "events"],
		status: "event_sources",
		noun: ["source", "sources"]
	},
	{ id: "WAF", label: "WAF", group: "data", keywords: ["firewall", "coraza"], status: "waf", noun: ["WAF", "WAFs"] },
	{
		id: "AI Triggers",
		label: "AI Triggers",
		group: "automation",
		subgroup: "AI",
		keywords: ["talon", "investigate", "ai analyst"],
		status: "ai_triggers"
	},
	{
		id: "AI Automation",
		label: "AI Automation",
		group: "automation",
		subgroup: "AI",
		keywords: ["talon", "policy", "levels"],
		requires: "automation"
	},
	{
		id: "Notification Workflows",
		label: "Notification Workflows",
		group: "automation",
		subgroup: "Notifications",
		keywords: ["shuffle", "workflow"],
		status: "notification_workflows",
		noun: ["workflow", "workflows"]
	},
	{
		id: "Notifications",
		label: "Notifications",
		group: "automation",
		subgroup: "Notifications",
		keywords: ["routes", "webhook", "teams", "email", "dispatch"],
		status: "notification_routes",
		noun: ["route", "routes"]
	},
	{ id: "Reporting", label: "Reporting", group: "reports", keywords: ["pdf", "report"] },
	{
		id: "Portal Branding",
		label: "Branding",
		group: "portal",
		subgroup: "Appearance",
		keywords: ["logo", "title", "brand color", "theme"],
		status: "portal_branding"
	},
	{
		id: "Portal Languages",
		label: "Languages",
		group: "portal",
		subgroup: "Appearance",
		keywords: ["locale", "translation", "italian"],
		status: "portal_languages"
	},
	{
		id: "SLA",
		label: "SLA",
		group: "portal",
		subgroup: "Portal pages",
		keywords: ["service levels"],
		status: "portal_sla"
	},
	{ id: "Activity", label: "Activity", group: "portal", subgroup: "Portal pages", status: "portal_activity" },
	{
		id: "Exposure",
		label: "Exposure",
		group: "portal",
		subgroup: "Portal pages",
		keywords: ["vulnerabilities", "compliance", "sca"],
		status: "portal_exposure"
	},
	{ id: "Audit Log", label: "Audit Log", group: "portal", subgroup: "Portal pages", status: "portal_audit" },
	{
		id: "AI Report",
		label: "AI Report",
		group: "portal",
		subgroup: "AI & requests",
		keywords: ["ai analyst", "talon", "chat"],
		status: "portal_ai_report"
	},
	{
		id: "Ask the SOC",
		label: "Ask the SOC",
		group: "portal",
		subgroup: "AI & requests",
		keywords: ["questions"],
		status: "portal_ask_soc"
	},
	{
		id: "IOC Enrichment",
		label: "IOC Enrichment",
		group: "portal",
		subgroup: "AI & requests",
		keywords: ["threat intel", "virustotal", "opencti"],
		status: "portal_ioc_enrichment"
	},
	{
		id: "Portal Notifications",
		label: "Notifications",
		group: "portal",
		subgroup: "Notifications",
		keywords: ["bell", "email", "digest"],
		status: "portal_notifications"
	}
]

export const DEFAULT_SECTION: SectionId = "Info"

const BY_ID = new Map(SECTIONS.map(section => [section.id, section]))

/** The tabs that held other tabs before the groups: a link to one opens its first section. */
const OLD_PARENT_TABS: Record<string, SectionId> = { Customer: "Info" }

export function isSectionId(value: string): value is SectionId {
	return BY_ID.has(value as SectionId)
}

export function sectionById(id: SectionId): SectionDef {
	return BY_ID.get(id) as SectionDef
}

export function groupById(id: GroupId): GroupDef {
	return GROUPS.find(group => group.id === id) as GroupDef
}

/** The section a `?tab=` value names, if any (an old parent tab opens its first section). */
export function tabToSection(tab: string | undefined | null): SectionId | null {
	if (!tab) return null
	if (isSectionId(tab)) return tab
	return OLD_PARENT_TABS[tab] ?? null
}

export type SectionGate = Record<SectionRequirement, boolean>

export function visibleSections(gate: SectionGate): SectionDef[] {
	return SECTIONS.filter(section => !section.requires || gate[section.requires])
}

export interface SubgroupView {
	/** Empty for a group's sections without a subgroup. */
	label: string
	sections: SectionDef[]
}

export interface GroupView extends GroupDef {
	sections: SectionDef[]
	subgroups: SubgroupView[]
}

/** The groups with the sections shown, in order; a group with none is left out. */
export function groupViews(sections: SectionDef[]): GroupView[] {
	return GROUPS.map(group => {
		const own = sections.filter(section => section.group === group.id)
		const subgroups: SubgroupView[] = []
		for (const section of own) {
			const label = section.subgroup ?? ""
			let subgroup = subgroups.find(item => item.label === label)
			if (!subgroup) {
				subgroup = { label, sections: [] }
				subgroups.push(subgroup)
			}
			subgroup.sections.push(section)
		}
		return { ...group, sections: own, subgroups }
	}).filter(group => group.sections.length > 0)
}

export type SectionState =
	| { kind: "switch"; on: boolean; word: string }
	| { kind: "count"; count: number; word: string }

function plural(count: number, noun: [string, string]): string {
	return `${count} ${count === 1 ? noun[0] : noun[1]}`
}

/** What a section holds for this customer, worded; null when unknown or not a switch or a list. */
export function sectionState(section: SectionDef, status: CustomerSectionStatus | null): SectionState | null {
	if (!status || !section.status) return null
	const value = status[section.status] as Partial<{ on: boolean; count: number; chat_on: boolean }> | undefined
	if (!value) return null
	if (section.status === "portal_languages" && typeof value.on === "boolean") {
		const count = value.count ?? 1
		return { kind: "switch", on: value.on, word: value.on ? plural(count, ["language", "languages"]) : "English only" }
	}
	if (section.status === "portal_ai_report" && typeof value.on === "boolean") {
		return { kind: "switch", on: value.on, word: value.on ? (value.chat_on ? "On · chat on" : "On") : "Off" }
	}
	if (typeof value.on === "boolean") return { kind: "switch", on: value.on, word: value.on ? "On" : "Off" }
	if (typeof value.count === "number") {
		const word = value.count === 0 ? "None" : plural(value.count, section.noun ?? ["entry", "entries"])
		return { kind: "count", count: value.count, word }
	}
	return null
}

/** "N of M on" for the switches among these sections; null when fewer than two are switches. */
export function switchSummary(sections: SectionDef[], status: CustomerSectionStatus | null): string | null {
	const states = sections.map(section => sectionState(section, status)).filter(state => state?.kind === "switch")
	if (states.length < 2) return null
	const on = states.filter(state => state?.kind === "switch" && state.on).length
	return `${on} of ${states.length} on`
}

function normalize(text: string): string {
	return text.toLocaleLowerCase().normalize("NFKD").replace(/\p{M}/gu, "").trim()
}

/** The sections a search finds: by label first, then by group, id or keyword; at most `limit`. */
export function searchSections(query: string, sections: SectionDef[], limit = 8): SectionDef[] {
	const words = normalize(query).split(/\s+/).filter(Boolean)
	if (!words.length) return []
	const scored: { section: SectionDef; score: number }[] = []
	for (const section of sections) {
		const label = normalize(section.label)
		const haystack = normalize(
			[section.label, section.id, groupById(section.group).label, section.subgroup ?? "", ...(section.keywords ?? [])].join(
				" "
			)
		)
		if (!words.every(word => haystack.includes(word))) continue
		const first = words[0] ?? ""
		const score = label.startsWith(first) ? 0 : label.includes(first) ? 1 : 2
		scored.push({ section, score })
	}
	return scored
		.sort((a, b) => a.score - b.score || SECTIONS.indexOf(a.section) - SECTIONS.indexOf(b.section))
		.slice(0, limit)
		.map(item => item.section)
}

/** Where a section sits, for the toolbar: "Customer Portal › AI & requests". */
export function sectionPath(section: SectionDef): string[] {
	return [groupById(section.group).label, ...(section.subgroup ? [section.subgroup] : [])]
}
