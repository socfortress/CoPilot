/**
 * The Talon v2 cost and run endpoints (CoPilot M5-9b over M5-9a's routes): each URL, its encoded
 * path segment, only the query parameters the route takes, the PUT body with both windows, and a
 * refusal read as its status and fixed text.
 */
import { AxiosError, AxiosHeaders } from "axios"
import { beforeEach, describe, expect, it, vi } from "vitest"

const get = vi.fn()
const put = vi.fn()

vi.mock("../http-client", () => ({
	HttpClient: { get: (...a: unknown[]) => get(...a), put: (...a: unknown[]) => put(...a) }
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => ({ userToken: null }) }))

const { default: talonUsage, talonFailure } = await import("../endpoints/talonUsage")

function refused(status: number, data: unknown) {
	const headers = new AxiosHeaders()
	return new AxiosError("refused", "ERR_BAD_REQUEST", { headers }, null, {
		status,
		statusText: "",
		data,
		headers,
		config: { headers }
	})
}

describe("talon usage endpoints", () => {
	beforeEach(() => {
		get.mockReset().mockResolvedValue({ data: {} })
		put.mockReset().mockResolvedValue({ data: {} })
	})

	it("usage: from, to, group_by and customer_code only, and no empty customer", () => {
		const signal = new AbortController().signal
		talonUsage.getUsage(
			{ from: "2026-09-17", to: "2026-10-16", group_by: "model", customer_code: "acme.io" },
			signal
		)
		expect(get).toHaveBeenCalledWith("/talon/v2/usage", {
			params: { from: "2026-09-17", to: "2026-10-16", group_by: "model", customer_code: "acme.io" },
			signal
		})
		talonUsage.getUsage({ from: "2026-09-17", to: "2026-10-16", customer_code: null })
		expect(get).toHaveBeenLastCalledWith("/talon/v2/usage", {
			params: { from: "2026-09-17", to: "2026-10-16" },
			signal: undefined
		})
	})

	it("one investigation's cost and run timeline, by the job id as a path segment", () => {
		talonUsage.getInvestigationUsage("copilot-inv-1-1760601600000")
		expect(get).toHaveBeenCalledWith("/talon/v2/usage/investigations/copilot-inv-1-1760601600000", {
			signal: undefined
		})
		talonUsage.getRunTimeline("a/b?c")
		expect(get).toHaveBeenLastCalledWith("/talon/v2/runs/a%2Fb%3Fc/timeline", { signal: undefined })
	})

	it("a thread's cost", () => {
		talonUsage.getThreadUsage("0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e")
		expect(get).toHaveBeenCalledWith("/talon/v2/usage/threads/0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e", {
			signal: undefined
		})
	})

	it("budgets: every customer, or one", () => {
		talonUsage.getBudgets()
		expect(get).toHaveBeenCalledWith("/talon/v2/budgets", { params: undefined, signal: undefined })
		talonUsage.getBudgets("ACME")
		expect(get).toHaveBeenLastCalledWith("/talon/v2/budgets", {
			params: { customer_code: "ACME" },
			signal: undefined
		})
	})

	it("a budget PUT sends exactly both windows, as strings or null", () => {
		talonUsage.putBudget("acme.io", { daily_usd: "12.50", monthly_usd: null })
		expect(put).toHaveBeenCalledWith("/talon/v2/budgets/acme.io", { daily_usd: "12.50", monthly_usd: null })
		talonUsage.putBudget("ACME", { daily_usd: "unlimited", monthly_usd: "300" })
		expect(put).toHaveBeenLastCalledWith("/talon/v2/budgets/ACME", { daily_usd: "unlimited", monthly_usd: "300" })
	})

	it("a refusal is its status and its short fixed text; no answer is the fixed failure", () => {
		expect(
			talonFailure(refused(409, { detail: "this customer's runs are not traced to a project of its own" }))
		).toEqual({
			status: 409,
			detail: "this customer's runs are not traced to a project of its own"
		})
		expect(talonFailure(refused(502, "<html>bad gateway</html>")).status).toBe(502)
		expect(talonFailure(refused(502, "<html>bad gateway</html>")).detail).not.toContain("<html>")
		expect(talonFailure(new Error("network")).status).toBeNull()
	})
})
