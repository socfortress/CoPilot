import { describe, expect, it } from "vitest"
import {
	agentLink,
	exportFilename,
	formatEpss,
	isWebLink,
	severityOptions,
	tabFromQuery,
	totalsLine,
	vulnerabilityStateFromQuery,
	withExposureQuery
} from "../exposure"

/** The Exposure page's URL state and how its figures read (#1289). */
describe("exposure URL state", () => {
	it("reads the tab, the first one when absent or unknown", () => {
		expect(tabFromQuery({})).toBe("vulnerabilities")
		expect(tabFromQuery({ tab: "compliance" })).toBe("compliance")
		expect(tabFromQuery({ tab: ["compliance", "vulnerabilities"] })).toBe("compliance")
		expect(tabFromQuery({ tab: "sca" })).toBe("vulnerabilities")
	})

	it("reads the filters, dropping what it cannot read", () => {
		expect(vulnerabilityStateFromQuery({ severity: "High", q: " openssl ", page: "3" })).toEqual({
			severity: "High",
			search: "openssl",
			page: 3
		})
		expect(vulnerabilityStateFromQuery({ severity: "high", page: "0" })).toEqual({
			severity: null,
			search: "",
			page: 1
		})
		expect(vulnerabilityStateFromQuery({ page: "two" }).page).toBe(1)
		expect(vulnerabilityStateFromQuery({ page: "-2" }).page).toBe(1)
		expect(vulnerabilityStateFromQuery({ q: "x".repeat(150) }).search).toHaveLength(100)
	})

	it("writes defaults out of the URL and keeps every other key", () => {
		expect(
			withExposureQuery({ other: "1", tab: "compliance" }, "vulnerabilities", {
				severity: null,
				search: " ",
				page: 1
			})
		).toEqual({ other: "1" })
		expect(withExposureQuery({}, "vulnerabilities", { severity: "Critical", search: "curl", page: 2 })).toEqual({
			severity: "Critical",
			q: "curl",
			page: "2"
		})
	})

	it("keeps the filters when only the tab changes, for the way back", () => {
		const query = { severity: "High", q: "curl", page: "2" }
		expect(withExposureQuery(query, "compliance")).toEqual({ ...query, tab: "compliance" })
		expect(withExposureQuery({ ...query, tab: "compliance" }, "vulnerabilities")).toEqual(query)
	})
})

describe("exposure figures", () => {
	it("gives every severity a count, missing ones zero, and All the sum", () => {
		const options = severityOptions([
			{ severity: "Critical", cves: 2, hosts: 1, findings: 3 },
			{ severity: "Low", cves: 5, hosts: 2, findings: 6 }
		])
		expect(options.map(o => [o.value, o.count])).toEqual([
			["All", 7],
			["Critical", 2],
			["High", 0],
			["Medium", 0],
			["Low", 5]
		])
		expect(severityOptions([], true).every(o => o.count === 0)).toBe(true)
	})

	it("reads EPSS as a percentage, with tiny ones and missing ones said so", () => {
		expect(formatEpss("0.97412")).toBe("97.4%")
		expect(formatEpss("0.0004")).toBe("<0.1%")
		expect(formatEpss("0")).toBe("0.0%")
		expect(formatEpss(null)).toBe("—")
		expect(formatEpss("")).toBe("—")
		expect(formatEpss("n/a")).toBe("—")
	})

	it("states the totals in the singular where it is one", () => {
		expect(totalsLine({ cves: 1, hosts: 1, findings: 1 })).toBe("1 CVE on 1 agent · 1 finding")
		expect(totalsLine({ cves: 1200, hosts: 3, findings: 4000 })).toBe(
			`${(1200).toLocaleString()} CVEs on 3 agents · ${(4000).toLocaleString()} findings`
		)
	})
})

describe("exposure links", () => {
	it("opens the agent on the tab the row came from, filtered to it", () => {
		expect(agentLink("001", { tab: "vulnerabilities", search: "CVE-2026-1" })).toEqual({
			name: "AgentDetails",
			params: { id: "001" },
			query: { tab: "vulnerabilities", search: "CVE-2026-1" }
		})
		expect(agentLink("002", { tab: "sca", policy: "cis_ubuntu22-04" })).toEqual({
			name: "AgentDetails",
			params: { id: "002" },
			query: { tab: "sca", policy: "cis_ubuntu22-04" }
		})
	})

	it("follows only web links", () => {
		expect(isWebLink("https://nvd.nist.gov/vuln/detail/CVE-2026-1")).toBe(true)
		expect(isWebLink("http://example.test/a")).toBe(true)
		expect(isWebLink("javascript:alert(1)")).toBe(false)
		expect(isWebLink("data:text/html,x")).toBe(false)
		expect(isWebLink("https://a.test/x y")).toBe(false)
		expect(isWebLink("CVE-2026-1")).toBe(false)
	})

	it("names the CSV after its filter and time, with no unsafe character", () => {
		const now = new Date("2026-10-20T09:08:07Z")
		expect(exportFilename({ severity: null, search: "" }, now)).toBe("vulnerabilities-2026-10-20-09-08-07.csv")
		expect(exportFilename({ severity: "High", search: "../open ssl" }, now)).toBe(
			"vulnerabilities-high-.._open_ssl-2026-10-20-09-08-07.csv"
		)
	})
})
