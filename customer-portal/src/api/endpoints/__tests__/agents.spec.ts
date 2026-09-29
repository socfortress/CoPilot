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
