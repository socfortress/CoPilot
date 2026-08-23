// Pure helpers for the File Analysis views (issue #974). They live outside the
// SFCs so the logic that is easy to get subtly wrong — which tabs exist for a
// given result, and collapsing a detonation's connection flood — is unit-testable
// without mounting a component or mocking the API.

import type { SandboxConnection } from "@/types/file-analysis"

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
