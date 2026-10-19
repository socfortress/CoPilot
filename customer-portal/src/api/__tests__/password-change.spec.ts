/**
 * A password an admin chose holds the user on the change (#1277): the API refuses every
 * other request with 403 and `X-Password-Change-Required`, and the client sends the user
 * to the change instead of showing the refusal on the page they are leaving.
 */

import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios"
import { AxiosError, AxiosHeaders } from "axios"
import { beforeEach, describe, expect, it, vi } from "vitest"

const store = vi.hoisted(() => ({ userToken: "token", refreshToken: vi.fn(), setPasswordChangeRequired: vi.fn() }))
const OVERVIEW = { name: "Overview", fullPath: "/overview?x=1", matched: [{}] }
const router = vi.hoisted(() => ({
	currentRoute: { value: { name: "Overview", fullPath: "/overview?x=1", matched: [{}] } as Record<string, unknown> },
	replace: vi.fn()
}))

vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
vi.mock("@/router", () => ({ default: router }))

const { createHttpClient, isPasswordChangeRequired } = await import("../httpClient")

function refusing(status: number, headers: Record<string, string>): AxiosAdapter {
	return (config: InternalAxiosRequestConfig) =>
		Promise.reject(
			new AxiosError("refused", String(status), config, null, {
				status,
				statusText: "",
				headers: new AxiosHeaders(headers),
				config,
				data: { success: false, message: "Choose a new password to continue." }
			})
		)
}

function flush() {
	return new Promise(resolve => setTimeout(resolve, 0))
}

beforeEach(() => {
	store.setPasswordChangeRequired.mockReset()
	router.replace.mockReset()
	router.currentRoute.value = OVERVIEW
})

describe("the password-change hold in the HTTP client (#1277)", () => {
	it("reads the header however axios hands it over", () => {
		expect(isPasswordChangeRequired(new AxiosHeaders({ "X-Password-Change-Required": "true" }))).toBe(true)
		expect(isPasswordChangeRequired({ "x-password-change-required": "true" })).toBe(true)
		expect(isPasswordChangeRequired({ "x-password-change-required": "false" })).toBe(false)
		expect(isPasswordChangeRequired(undefined)).toBe(false)
	})

	it("sends the user to the change and leaves the refused request unsettled", async () => {
		const client = createHttpClient("/api")
		const settled = vi.fn()
		client
			.get("/customer_portal/overview", { adapter: refusing(403, { "X-Password-Change-Required": "true" }) })
			.then(settled, settled)
		await flush()
		await flush()
		expect(store.setPasswordChangeRequired).toHaveBeenCalledWith(true)
		expect(router.replace).toHaveBeenCalledWith({ name: "ChangePassword", query: { redirect: "/overview?x=1" } })
		expect(settled).not.toHaveBeenCalled()
	})

	it("does not navigate again from the change itself", async () => {
		router.currentRoute.value = { name: "ChangePassword", fullPath: "/change-password", matched: [{}] }
		const client = createHttpClient("/api")
		client.get("/x", { adapter: refusing(403, { "X-Password-Change-Required": "true" }) }).catch(() => {})
		await flush()
		await flush()
		expect(router.replace).not.toHaveBeenCalled()
	})

	it("leaves the first navigation to the router's guard, which knows where the user was going", async () => {
		// A page loaded directly: requests start before the first navigation settles, while
		// the current route is still the start location.
		router.currentRoute.value = { name: undefined, fullPath: "/", matched: [] }
		const client = createHttpClient("/api")
		client.get("/x", { adapter: refusing(403, { "X-Password-Change-Required": "true" }) }).catch(() => {})
		await flush()
		await flush()
		expect(store.setPasswordChangeRequired).toHaveBeenCalledWith(true)
		expect(router.replace).not.toHaveBeenCalled()
	})

	it("leaves any other 403 to the caller", async () => {
		const client = createHttpClient("/api")
		await expect(client.get("/x", { adapter: refusing(403, {}) })).rejects.toBeInstanceOf(AxiosError)
		expect(store.setPasswordChangeRequired).not.toHaveBeenCalled()
		expect(router.replace).not.toHaveBeenCalled()
	})
})
