// Pure helpers for the File Analysis views (issue #974). They live outside the
// SFCs so the logic that is easy to get subtly wrong — which tabs exist for a
// given result, and collapsing a detonation's connection flood — is unit-testable
// without mounting a component or mocking the API.

import type { FileAnalysisVerdict, SandboxConnection } from "@/types/file-analysis"

/** The tab keys rendered by views/FileAnalysis.vue, in display order. */
export type FileAnalysisTab = "preview" | "content" | "iocs" | "virustotal" | "metadata" | "detonation" | "network"

/** Whether each optional tab has something to show. Metadata is always present. */
export interface TabAvailability {
	previews?: boolean
	content?: boolean
	iocs?: boolean
	vtIntel?: boolean
	sandbox?: boolean
}

/**
 * Tabs that currently exist, in the order they are rendered. Empty ones are
 * hidden — the file types this module handles rarely populate every tab, and a
 * blank "Preview" for a PE was the original complaint.
 */
export function availableTabs(flags: TabAvailability): FileAnalysisTab[] {
	const tabs: FileAnalysisTab[] = []
	if (flags.previews) tabs.push("preview")
	if (flags.content) tabs.push("content")
	if (flags.iocs) tabs.push("iocs")
	if (flags.vtIntel) tabs.push("virustotal")
	tabs.push("metadata")
	// Detonation and Network are gated on the backend reporting a sandbox, not on
	// having a report — an in-flight detonation must still be reachable.
	if (flags.sandbox) tabs.push("detonation", "network")
	return tabs
}

/**
 * The tab to show after availability changes.
 *
 * Two rules, and the order matters. Until the analyst picks a tab themselves we
 * follow the content: the result arrives by polling, so a job opens with only
 * Metadata and gains Preview/Content/IOCs seconds later — auto-following is what
 * makes the view land on the page images of a PDF instead of its hash table.
 * Once they have picked, we stay put as long as that tab exists, so a VirusTotal
 * scan landing 30s in cannot yank a reader off the Detonation tab.
 *
 * Metadata is always available, which is why "keep the current tab" cannot be the
 * only rule — it would pin the view to the initial Metadata forever.
 */
export function resolveActiveTab(
	current: string | null | undefined,
	flags: TabAvailability,
	pinnedByUser = false
): FileAnalysisTab {
	const tabs = availableTabs(flags)
	if (pinnedByUser && current && (tabs as string[]).includes(current)) return current as FileAnalysisTab
	return tabs[0]
}

export interface GroupedConnection {
	proto: string
	dst: string
	dport?: number
	count: number
}

/**
 * A detonation typically logs the same endpoint (DNS resolver, multicast address,
 * gateway) hundreds of times. Collapse identical proto+dst+dport tuples into one
 * counted row so the analyst sees the handful of distinct endpoints, ranked by
 * chattiness. Protocol is lower-cased so "TCP" and "tcp" are one row.
 */
export function groupConnections(connections: SandboxConnection[] | undefined | null): GroupedConnection[] {
	const map = new Map<string, GroupedConnection>()
	for (const c of connections ?? []) {
		const proto = (c.proto || "").toLowerCase()
		const key = `${proto}|${c.dst}|${c.dport ?? ""}`
		const existing = map.get(key)
		if (existing) existing.count += 1
		else map.set(key, { proto, dst: c.dst, dport: c.dport, count: 1 })
	}
	return Array.from(map.values()).sort((a, b) => b.count - a.count)
}

// Extension → icon. Scanning collected files is mostly asking "which of these is
// executable content", so the families that answer that get their own glyph and
// everything else falls back to a plain document.
const FILE_ICONS: Record<string, string> = {
	exe: "carbon:executable-program",
	dll: "carbon:executable-program",
	sys: "carbon:executable-program",
	elf: "carbon:executable-program",
	so: "carbon:executable-program",
	bin: "carbon:executable-program",
	ps1: "carbon:script",
	sh: "carbon:script",
	bat: "carbon:script",
	cmd: "carbon:script",
	py: "carbon:script",
	js: "carbon:script",
	vbs: "carbon:script",
	hta: "carbon:script",
	zip: "carbon:archive",
	"7z": "carbon:archive",
	rar: "carbon:archive",
	gz: "carbon:archive",
	tar: "carbon:archive",
	cab: "carbon:archive",
	pdf: "carbon:document-pdf",
	png: "carbon:image",
	jpg: "carbon:image",
	jpeg: "carbon:image",
	gif: "carbon:image",
	svg: "carbon:image",
	bmp: "carbon:image",
	txt: "carbon:document-blank",
	log: "carbon:document-blank",
	csv: "carbon:document-blank",
	json: "carbon:code",
	xml: "carbon:code"
}

export function iconForFile(name: string | null | undefined): string {
	const ext = (name || "").split(".").pop()?.toLowerCase() || ""
	return FILE_ICONS[ext] || "carbon:document"
}

/* -------------------------------------------------------------------------- */
/*  Verdict and source presentation                                           */
/* -------------------------------------------------------------------------- */

/*
 * One verdict, one appearance. These mappings used to be re-typed in every view
 * that showed a verdict — the header, the batch drawer, the history list and the
 * detonation tab — and the copies had already drifted apart: two of them knew
 * about the "flow" source and two did not.
 */

export type VerdictTagType = "success" | "warning" | "error" | "default"

/** Naive tag/alert type for a verdict. */
export function verdictTagType(verdict: FileAnalysisVerdict | null | undefined): VerdictTagType {
	if (verdict === "malicious") return "error"
	if (verdict === "suspicious") return "warning"
	if (verdict === "clean") return "success"
	return "default"
}

/** Icon for a verdict; callers with their own states (running, failed) handle those first. */
export function verdictIcon(verdict: FileAnalysisVerdict | null | undefined): string {
	if (verdict === "malicious") return "carbon:warning-alt-filled"
	if (verdict === "suspicious") return "carbon:warning-alt"
	return "carbon:checkmark-filled"
}

/**
 * Accent for a row or card. Only a judged-bad verdict carries one: painting a
 * clean row green makes a list of ordinary files look like a wall of alarms.
 */
export function verdictAccent(verdict: FileAnalysisVerdict | null | undefined): "warning" | "error" | undefined {
	if (verdict === "malicious") return "error"
	if (verdict === "suspicious") return "warning"
	return undefined
}

/** Text colour class for a verdict. */
export function verdictTextClass(verdict: FileAnalysisVerdict | null | undefined): string {
	if (verdict === "malicious") return "text-error"
	if (verdict === "suspicious") return "text-warning"
	return "text-secondary"
}

/**
 * A resolved colour for canvases and Naive props that take a colour rather than a
 * class (progress rings, charts). Theme variables, not hex literals — hardcoded
 * ones ignored the light/dark switch and any brand override.
 */
export function verdictColorVar(verdict: FileAnalysisVerdict | null | undefined): string {
	if (verdict === "malicious") return "var(--error-color)"
	if (verdict === "suspicious") return "var(--warning-color)"
	return "var(--success-color)"
}

const SOURCE_LABELS: Record<string, string> = {
	upload: "uploaded",
	host_path: "collected from endpoint",
	flow: "from flow"
}

/** How the sample reached CoPilot, in words. */
export function sourceLabel(source: string | null | undefined): string {
	return SOURCE_LABELS[source || ""] || source || "—"
}

/** How the sample reached CoPilot, as an icon. */
export function sourceIcon(source: string | null | undefined): string {
	return source === "upload" ? "carbon:cloud-upload" : "carbon:bare-metal-server"
}

/* -------------------------------------------------------------------------- */
/*  Indicator lookups                                                          */
/* -------------------------------------------------------------------------- */

/** Indicators are stored defanged (example[.]com); a lookup URL needs them intact. */
export function refang(value: string): string {
	return value.replaceAll("[.]", ".").replaceAll("[:]", ":")
}

/** VirusTotal page for an indicator — the one place the GUI URL shape is written. */
export function virusTotalUrl(indicator: string, kind: "ip" | "domain" | "file" = "ip"): string {
	const path = kind === "domain" ? "domain" : kind === "file" ? "file" : "ip-address"
	return `https://www.virustotal.com/gui/${path}/${encodeURIComponent(refang(indicator))}`
}

/** True for a bare IPv4 literal — the only shape worth a reputation lookup. */
export function looksLikeIp(value: string): boolean {
	return /^\d{1,3}(?:\.\d{1,3}){3}$/.test(value || "")
}
