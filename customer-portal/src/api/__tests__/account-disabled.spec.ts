/**
 * An account disabled while its session is open (#1296): the API answers its next request 401
 * with `X-Account-Disabled`, and the client signs the user out to a sign-in page that says why.
 */

import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios"
import { AxiosError, AxiosHeaders } from "axios"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/stores/auth", () => ({ useAuthStore: () => ({ userToken: "token", refreshToken: vi.fn() }) }))
vi.mock("@/router", () => ({ default: { currentRoute: { value: { matched: [] } }, replace: vi.fn() } }))

const { createHttpClient, isAccountDisabled } = await import("../httpClient")

function refusing(headers: Record<string, string>): AxiosAdapter {
	return (config: InternalAxiosRequestConfig) =>
		Promise.reject(
			new AxiosError("refused", "401", config, null, {
				status: 401,
				statusText: "",
				headers: new AxiosHeaders(headers),
				config,
				data: { success: false, message: "This account is disabled. Ask your organization's administrator or your SOC to enable it again." }
			})
		)
}

const location = { href: "", pathname: "/overview" }

beforeEach(() => {
	location.href = ""
	location.pathname = "/overview"
	vi.stubGlobal("location", location)
})

afterEach(() => {
	vi.unstubAllGlobals()
})

describe("a disabled account in the HTTP client (#1296)", () => {
	it("reads the header however axios hands it over", () => {
		expect(isAccountDisabled(new AxiosHeaders({ "X-Account-Disabled": "true" }))).toBe(true)
		expect(isAccountDisabled({ "x-account-disabled": "true" })).toBe(true)
		expect(isAccountDisabled({})).toBe(false)
		expect(isAccountDisabled(undefined)).toBe(false)
	})

	it("signs the user out to a sign-in page that says the account was disabled", async () => {
		await createHttpClient("/api")
			.get("/customer_portal/me", { adapter: refusing({ "X-Account-Disabled": "true" }) })
			.catch(() => {})
		expect(location.href).toBe("/logout?reason=disabled")
	})

	it("signs any other 401 out without a reason", async () => {
		await createHttpClient("/api")
			.get("/customer_portal/me", { adapter: refusing({}) })
			.catch(() => {})
		expect(location.href).toBe("/logout")
	})
})
