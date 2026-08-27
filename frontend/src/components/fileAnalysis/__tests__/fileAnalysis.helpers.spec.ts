import type { SandboxConnection } from "@/types/file-analysis"
import { describe, expect, it } from "vitest"
import { availableTabs, groupConnections, resolveActiveTab } from "../fileAnalysis.helpers"

describe("availableTabs", () => {
	it("always offers Metadata, even for a result with nothing else", () => {
		expect(availableTabs({})).toEqual(["metadata"])
	})

	it("hides tabs that have no content", () => {
		expect(availableTabs({ iocs: true })).toEqual(["iocs", "metadata"])
	})

	it("keeps the rendered display order", () => {
		expect(availableTabs({ previews: true, content: true, iocs: true, vtIntel: true })).toEqual([
			"preview",
			"content",
			"iocs",
			"virustotal",
			"metadata"
		])
	})

	it("adds Detonation and Network when the backend reports a sandbox", () => {
		expect(availableTabs({ sandbox: true })).toEqual(["metadata", "detonation", "network"])
	})
})

describe("resolveActiveTab", () => {
	it("lands on the first populated tab when nothing is selected yet", () => {
		expect(resolveActiveTab(null, { previews: true, iocs: true })).toBe("preview")
	})

	it("falls back to Metadata when the file populated no other tab", () => {
		expect(resolveActiveTab(null, {})).toBe("metadata")
	})

	// A job opens with only Metadata and gains its real tabs as the poll fills the
	// result in. Because Metadata is always available, a plain "keep the current
	// tab" rule would pin the view to it forever — that was the bug here.
	it("follows the content off the initial Metadata once previews arrive", () => {
		expect(resolveActiveTab("metadata", { previews: true })).toBe("preview")
	})

	it("keeps following the content while the analyst has not picked a tab", () => {
		expect(resolveActiveTab("content", { previews: true, content: true })).toBe("preview")
	})

	// Moving the analyst off the tab they are reading is the other half of the bug.
	it("stays on a tab the analyst picked when a VirusTotal scan lands later", () => {
		const before = { sandbox: true }
		expect(resolveActiveTab("detonation", before, true)).toBe("detonation")
		expect(resolveActiveTab("detonation", { ...before, vtIntel: true, iocs: true }, true)).toBe("detonation")
	})

	it("keeps a picked tab when unrelated tabs appear", () => {
		expect(resolveActiveTab("iocs", { iocs: true, previews: true, content: true }, true)).toBe("iocs")
	})

	it("moves off a picked tab that stopped existing", () => {
		expect(resolveActiveTab("preview", { iocs: true }, true)).toBe("iocs")
	})

	it("ignores a tab name it does not know", () => {
		expect(resolveActiveTab("does-not-exist", { content: true }, true)).toBe("content")
	})
})

describe("groupConnections", () => {
	const conn = (proto: string, dst: string, dport?: number): SandboxConnection => ({ proto, dst, dport })

	it("returns nothing for a detonation with no traffic", () => {
		expect(groupConnections(undefined)).toEqual([])
		expect(groupConnections([])).toEqual([])
	})

	it("collapses repeats of the same endpoint into one counted row", () => {
		const grouped = groupConnections([conn("tcp", "1.1.1.1", 443), conn("tcp", "1.1.1.1", 443)])
		expect(grouped).toHaveLength(1)
		expect(grouped[0].count).toBe(2)
	})

	it("treats a different port as a different endpoint", () => {
		expect(groupConnections([conn("tcp", "1.1.1.1", 443), conn("tcp", "1.1.1.1", 80)])).toHaveLength(2)
	})

	it("normalises protocol case so TCP and tcp are one row", () => {
		const grouped = groupConnections([conn("TCP", "1.1.1.1", 443), conn("tcp", "1.1.1.1", 443)])
		expect(grouped).toHaveLength(1)
		expect(grouped[0].proto).toBe("tcp")
	})

	it("ranks the chattiest endpoint first", () => {
		const grouped = groupConnections([
			conn("udp", "8.8.8.8", 53),
			conn("tcp", "10.0.0.1", 445),
			conn("udp", "8.8.8.8", 53),
			conn("udp", "8.8.8.8", 53)
		])
		expect(grouped[0]).toMatchObject({ dst: "8.8.8.8", count: 3 })
		expect(grouped[1]).toMatchObject({ dst: "10.0.0.1", count: 1 })
	})
})
