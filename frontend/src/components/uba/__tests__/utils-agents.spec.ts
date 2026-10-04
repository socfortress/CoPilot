import type { UbaAgentsSummary, UbaHost } from "@/types/uba"
import { describe, expect, it } from "vitest"
import { agentsSummaryTitle, silentComputers } from "../utils"

function host(name: string, lastKeepalive: string | null): UbaHost {
	return {
		agent_id: name,
		name,
		os: null,
		platform: null,
		role: null,
		ip: null,
		status: "disconnected",
		reporting: "not_reporting",
		last_keepalive: lastKeepalive,
		agent_version: null,
		groups: [],
		registered_at: null,
		updated_at: null
	}
}

const SUMMARY: UbaAgentsSummary = {
	total: 30,
	reporting: 5,
	not_reporting: 22,
	retired: 2,
	never_connected: 1,
	not_reporting_hosts: [host("WS02", "2026-10-04T18:00:00Z"), host("DC01", null)],
	updated_at: null
}

describe("uba computers", () => {
	it("names the computers not reporting, then how many more", () => {
		expect(silentComputers(SUMMARY, t => t.slice(11, 16))).toBe("WS02 (since 18:00), DC01 and 20 more")
		expect(silentComputers({ ...SUMMARY, not_reporting: 2 }, t => t)).not.toContain("more")
	})

	it("counts computers without the retired ones", () => {
		expect(agentsSummaryTitle(SUMMARY).split("\n")).toEqual([
			"5 of 28 computers with a Wazuh agent are reporting",
			"2 silent for over 30 days (not counted)",
			"1 enrolled but never connected"
		])
	})
})
