// TEMPORARY mock data for the "Collect from an endpoint" panel (issue #974).
//
// Why this exists: the file-selection UI cannot be exercised without a live
// Velociraptor reachable from the dev host — no agents means the path box stays
// disabled, and no matches means the picker never renders. This stands in for
// both read calls so the selection flow can be developed and reviewed offline.
//
// SAFETY: gated on `import.meta.env.DEV`, so it is impossible for this to serve
// data in a production build even if someone forgets to remove it. Set
// USE_MOCK_COLLECT to false to talk to the real backend while still in dev.
//
// TO REMOVE: delete this file plus the three `USE_MOCK_COLLECT` branches in
// CollectPanel.vue (loadAgents, findFiles, analyzeSelected). Nothing else
// imports it.

import type { FileAnalysisAgent, FileAnalysisMatch } from "@/types/file-analysis"

/** The switch. Currently off: the panel talks to the real backend. */
const MOCK_COLLECT_ENABLED = false

/** DEV-guarded as well, so it can never serve data from a production build. */
export const USE_MOCK_COLLECT = import.meta.env.DEV && MOCK_COLLECT_ENABLED

/** Stand-in latency, so loading states and disabled-while-busy actually show. */
const LATENCY_MS = 600

function delay<T>(value: T, ms = LATENCY_MS): Promise<T> {
	return new Promise(resolve => setTimeout(resolve, ms, value))
}

// A deterministic 64-hex string per file, so a given mock path always keeps the
// same hash — the history cache is keyed on sha256, and a hash that changed per
// render would look like a different file on every search.
function fakeSha256(seed: string): string {
	let h1 = 0x12345678
	let h2 = 0x9abcdef0
	for (let i = 0; i < seed.length; i++) {
		h1 = Math.imul(h1 ^ seed.charCodeAt(i), 2654435761) >>> 0 || 1
		h2 = Math.imul(h2 + seed.charCodeAt(i), 1597334677) >>> 0 || 1
	}
	let out = ""
	let a = h1
	let b = h2
	while (out.length < 64) {
		a = (Math.imul(a, 1664525) + 1013904223) >>> 0
		b = (Math.imul(b, 22695477) + 1) >>> 0
		// >>> 0 is load-bearing: XOR yields a SIGNED int32 in JS, and toString(16) on a
		// negative produces a leading "-", which is not a hex digit.
		out += ((a ^ b) >>> 0).toString(16).padStart(8, "0")
	}
	return out.slice(0, 64)
}

// Deliberately mixed: online and offline, three OS families, and one endpoint not
// assigned to any customer — those are the three branches renderAgentLabel draws.
const AGENTS: FileAnalysisAgent[] = [
	{
		client_id: "C.1a2b3c4d5e6f7a8b",
		hostname: "WIN-SQL-01",
		os: "windows",
		online: true,
		last_seen: Date.now() - 45_000,
		unassigned: false
	},
	{
		client_id: "C.2b3c4d5e6f7a8b9c",
		hostname: "WIN-DC-01",
		os: "windows",
		online: true,
		last_seen: Date.now() - 120_000,
		unassigned: false
	},
	{
		client_id: "C.3c4d5e6f7a8b9c0d",
		hostname: "ubuntu-web-02",
		os: "linux",
		online: true,
		last_seen: Date.now() - 8_000,
		unassigned: false
	},
	{
		client_id: "C.4d5e6f7a8b9c0d1e",
		hostname: "macbook-analyst",
		os: "darwin",
		online: false,
		last_seen: Date.now() - 3 * 3600_000,
		unassigned: false
	},
	{
		client_id: "C.5e6f7a8b9c0d1e2f",
		hostname: "orphan-host-77",
		os: "linux",
		online: false,
		last_seen: Date.now() - 26 * 3600_000,
		unassigned: true
	}
]

export function mockListAgents(): Promise<FileAnalysisAgent[]> {
	return delay(AGENTS)
}

function match(path: string, size: number): FileAnalysisMatch {
	const name = path.split(/[\\/]/).pop() || path
	return { path, name, size, sha256: fakeSha256(path) }
}

const WINDOWS_MATCHES: FileAnalysisMatch[] = [
	match("C:\\Users\\jdoe\\Downloads\\invoice_2026_08.docm", 84_213),
	match("C:\\Users\\jdoe\\Downloads\\setup_helper.exe", 2_918_400),
	match("C:\\Users\\jdoe\\Downloads\\statement.pdf", 412_887),
	match("C:\\Users\\jdoe\\Downloads\\update.ps1", 3_142),
	match("C:\\Users\\jdoe\\Downloads\\archive.zip", 15_884_221)
]

const UNIX_MATCHES: FileAnalysisMatch[] = [
	match("/tmp/stage/payload.elf", 1_204_992),
	match("/tmp/stage/collect.sh", 2_048),
	match("/tmp/stage/notes.txt", 512)
]

/**
 * Mock enumeration. The path drives the outcome, so every branch of the picker
 * can be reached from the UI without editing code:
 *
 *   …/empty…  → no matches (empty state)
 *   …/fail…   → rejects (inline error box)
 *   …/one…    → exactly one match (auto-selected on arrival)
 *   anything else → a multi-file list, Windows- or Unix-flavoured by the path
 */
export function mockEnumerate(targetPath: string): Promise<FileAnalysisMatch[]> {
	const path = targetPath.toLowerCase()

	if (path.includes("fail")) {
		return new Promise((_resolve, reject) =>
			setTimeout(() => reject(new Error("mock: endpoint did not respond within 30s")), LATENCY_MS)
		)
	}
	if (path.includes("empty")) return delay([])

	const isWindows = targetPath.includes("\\") || /^[a-z]:/i.test(targetPath)
	const pool = isWindows ? WINDOWS_MATCHES : UNIX_MATCHES
	if (path.includes("one")) return delay([pool[0]])
	return delay(pool)
}

/** Fake job ids for a mocked submission — same shape as the backend's uuid4. */
export function mockSubmit(paths: string[]): Promise<string[]> {
	return delay(
		paths.map(p => fakeSha256(`job:${p}`).replace(/^(.{8})(.{4})(.{4})(.{4})(.{12}).*$/, "$1-$2-$3-$4-$5"))
	)
}
