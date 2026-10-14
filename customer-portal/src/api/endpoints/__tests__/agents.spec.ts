import { beforeEach, describe, expect, it, vi } from "vitest"
import agents from "../agents"

const get = vi.hoisted(() => vi.fn())
vi.mock("../../httpClient", () => ({ HttpClient: { get } }))

describe("agents endpoints (server-side list, #1185)", () => {
	beforeEach(() => {
		get.mockReset()
	})

	it("sends page, size and only the filters that are set", () => {
		agents.getAgentsPage({ page: 2, pageSize: 50, search: "web", status: null, os: "", critical: false })
		const [url, config] = get.mock.calls[0]!
		expect(url).toBe("/customer_portal/agents")
		expect(config.params).toEqual({
			page: 2,
			page_size: 50,
			search: "web",
			status: undefined,
			os: undefined,
			critical: undefined
		})
	})

	it("scopes to the selected customers with repeated query params", () => {
		agents.getAgentsPage({ page: 1, pageSize: 25, critical: true, customerCodes: ["A", "B"] })
		const [, config] = get.mock.calls[0]!
		expect(config.params).toMatchObject({ critical: true, customer_codes: ["A", "B"] })
		expect(config.paramsSerializer).toEqual({ indexes: null })
	})

	it("exports the same filters as a blob, without paging", () => {
		agents.exportAgents({ search: "web", status: "active" })
		const [url, config] = get.mock.calls[0]!
		expect(url).toBe("/customer_portal/agents/export")
		expect(config.responseType).toBe("blob")
		expect(config.params).toMatchObject({ search: "web", status: "active", page: undefined, page_size: undefined })
	})
})

/** An agent's tabs (#1256): ids and host names travel encoded; exports are blobs kept across navigation. */
describe("agents endpoints: an agent's findings", () => {
	beforeEach(() => {
		get.mockReset()
	})

	it("asks for every severity at once: the page filters", () => {
		const signal = new AbortController().signal
		agents.getVulnerabilities("001", signal)
		expect(get.mock.calls[0]).toEqual(["/agents/001/vulnerabilities/All", { signal }])
	})

	it("encodes the agent id, the policy id and the host name", () => {
		agents.getScaChecks("a/b", "cis ubuntu")
		agents.getCases("web 01/x")
		expect(get.mock.calls[0]![0]).toBe("/agents/a%2Fb/sca/cis%20ubuntu")
		expect(get.mock.calls[1]![0]).toBe("/agents/web%2001%2Fx/cases")
	})

	it("downloads both exports as blobs that outlive a navigation", () => {
		agents.exportVulnerabilities("001", "Critical")
		agents.exportScaChecks("001", "cis_ubuntu22-04")
		expect(get.mock.calls.map(([url, config]) => [url, config.responseType, config.keepOnNavigation])).toEqual([
			["/agents/001/csv/vulnerabilities/Critical", "blob", true],
			["/agents/001/csv/sca/cis_ubuntu22-04", "blob", true]
		])
	})
})
