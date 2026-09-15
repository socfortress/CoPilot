/**
 * Which 401s log the user out (#1133).
 *
 * The response interceptor used to treat every 401 as an expired session. A
 * request the browser redirected across origins loses its Authorization header
 * and comes back 401 for a user whose token is perfectly valid — that is the path
 * a `C:\` search term took. The rule pinned here: only a 401 served from the URL
 * we asked for is the backend rejecting our token.
 */

import type { AxiosError, InternalAxiosRequestConfig } from "axios"
import { describe, expect, it } from "vitest"
import { isSessionExpiry } from "../session-expiry"

function axiosError(status: number, config: Partial<InternalAxiosRequestConfig>, responseURL?: string): AxiosError {
	return {
		config: { headers: {}, ...config } as InternalAxiosRequestConfig,
		request: responseURL === undefined ? undefined : { responseURL },
		response: { status, data: {}, statusText: "", headers: {}, config: {} as InternalAxiosRequestConfig }
	} as unknown as AxiosError
}

const ORIGIN = window.location.origin

describe("isSessionExpiry", () => {
	it("ignores anything that is not a 401", () => {
		expect(
			isSessionExpiry(axiosError(403, { baseURL: "/api", url: "/customers" }, `${ORIGIN}/api/customers`))
		).toBe(false)
		expect(
			isSessionExpiry(axiosError(500, { baseURL: "/api", url: "/customers" }, `${ORIGIN}/api/customers`))
		).toBe(false)
	})

	it("is an expiry when the 401 was served from the URL we requested", () => {
		const error = axiosError(
			401,
			{ baseURL: "/api", url: "/customers", params: { search: "acme", limit: 5 } },
			`${ORIGIN}/api/customers?search=acme&limit=5`
		)
		expect(isSessionExpiry(error)).toBe(true)
	})

	it("is not an expiry when the browser followed a redirect first", () => {
		// What a `C:\` title search produced: the browser sent `.../title/C:/`, the
		// backend redirected to `.../title/C:` on another origin, the token was dropped.
		const error = axiosError(
			401,
			{ baseURL: "/api", url: "/incidents/db_operations/alerts/title/C:\\", params: { page: 1 } },
			`${ORIGIN}/api/incidents/db_operations/alerts/title/C:`
		)
		expect(isSessionExpiry(error)).toBe(false)
	})

	it("compares against the URL as the browser normalises it, so an unredirected request still matches", () => {
		// No redirect happened; the served URL is just the requested one after normalisation.
		const error = axiosError(
			401,
			{ baseURL: "/api", url: "/incidents/db_operations/alerts/title/C:\\", params: { page: 1 } },
			`${ORIGIN}/api/incidents/db_operations/alerts/title/C:/?page=1`
		)
		expect(isSessionExpiry(error)).toBe(true)
	})

	it("keeps the historical behaviour when the served URL is unknown", () => {
		expect(isSessionExpiry(axiosError(401, { baseURL: "/api", url: "/customers" }))).toBe(true)
		expect(isSessionExpiry(axiosError(401, { baseURL: "/api", url: "/customers" }, ""))).toBe(true)
	})
})
