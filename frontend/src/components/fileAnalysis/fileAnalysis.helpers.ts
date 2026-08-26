// Pure helpers for the File Analysis views (issue #974). They live outside the
// SFCs so the logic that is easy to get subtly wrong — which tabs exist for a
// given result, and collapsing a detonation's connection flood — is unit-testable
// without mounting a component or mocking the API.

import type { Ref } from "vue"
import type { SandboxConnection } from "@/types/file-analysis"
import { computed, ref } from "vue"
import { createFuse, searchFuse } from "@/components/common/searchDialog.helpers"

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

/**
 * A client-side filter over one of a report's lists. Nothing is requested as the
 * analyst types — Fuse searches the array already delivered with the report.
 * Fuzzy rather than a substring match, so "base64" still finds "encode data using
 * Base64" and a typo in a rule or process name does not blank the list.
 *
 * `source` is a getter rather than a value so the index follows a computed list
 * that arrives later, which is always the case while a job is still polling.
 */
export function useFuseFilter<T>(source: () => T[], keys: string[]): { query: Ref<string>; results: Ref<T[]> } {
	const query = ref("")
	const fuse = computed(() => createFuse(source(), keys))
	const results = computed(() => searchFuse(fuse.value, query.value, source()))
	return { query, results }
}
