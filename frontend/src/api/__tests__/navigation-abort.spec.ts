/**
 * Navigation-scoped request cancellation (#1072).
 *
 * The first attempt at this only added a `signal` parameter to the endpoint
 * wrappers and fixed unmount cleanup in the ~40 components that already owned a
 * controller. That silently did nothing on pages like Overview, which never
 * created one — leaving a page still left its loads running. These tests pin the
 * behaviour that replaced it, including the three rules that keep it safe.
 *
 * Each test asserts on the signal the adapter actually received. Asserting only
 * that a promise stays pending would not distinguish "aborted and deliberately
 * swallowed" from "never aborted at all" — which is precisely how the first
 * attempt looked fine while doing nothing.
 */

import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios"
import axios from "axios"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({ userToken: null, refreshToken: vi.fn() })
}))

const { HttpClient } = await import("../http-client")
const { resetNavigationScope } = await import("../navigation-abort")

interface Captured {
	signal?: AbortSignal
}

/** Never answers, so the request stays in flight; records the signal it was given. */
function hangingAdapter(captured: Captured): AxiosAdapter {
	return (config: InternalAxiosRequestConfig) => {
		// axios types `signal` loosely as GenericAbortSignal; at runtime it is the
		// real AbortSignal we (or the caller) attached.
		const signal = config.signal as AbortSignal | undefined
		captured.signal = signal
		return new Promise<never>((_resolve, reject) => {
			signal?.addEventListener("abort", () => {
				// Mirrors what axios throws on abort, so `axios.isCancel` holds.
				const error = Object.assign(new Error("canceled"), {
					code: "ERR_CANCELED",
					config,
					__CANCEL__: true
				})
				reject(error)
			})
		})
	}
}

/** Let the axios interceptor chain run: it spans several microtasks before the adapter is called. */
function flush() {
	return new Promise(resolve => setTimeout(resolve, 0))
}

/** How the promise settled, without hanging the test forever. */
function settlement(promise: Promise<unknown>) {
	return Promise.race([
		promise.then(
			() => "resolved",
			error => (axios.isCancel(error) ? "rejected:cancel" : "rejected:other")
		),
		new Promise(resolve => setTimeout(resolve, 50, "pending"))
	])
}

describe("navigation-scoped request cancellation", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetNavigationScope()
	})

	it("aborts an in-flight GET when the route changes", async () => {
		const captured: Captured = {}
		const request = HttpClient.get("/overview/agents", { adapter: hangingAdapter(captured) })
		await flush()

		expect(captured.signal, "the GET should have been given the navigation signal").toBeDefined()
		expect(captured.signal?.aborted).toBe(false)

		resetNavigationScope() // what the router does on a path change

		// The real assertion: the request was actually aborted, not merely quiet.
		expect(captured.signal?.aborted).toBe(true)

		// And it never settles, so the ~340 components that do not guard with
		// `axios.isCancel` cannot pop an error toast on every navigation.
		await expect(settlement(request)).resolves.toBe("pending")
	})

	it("leaves mutations unattached — aborting one would only hide whether it happened", async () => {
		const captured: Captured = {}
		HttpClient.post("/incidents/cases", {}, { adapter: hangingAdapter(captured) })
		await flush()

		expect(captured.signal).toBeUndefined()

		resetNavigationScope()
		expect(captured.signal).toBeUndefined()
	})

	it("does not take over a request that brought its own signal", async () => {
		const own = new AbortController()
		const captured: Captured = {}
		const request = HttpClient.get("/agents", { signal: own.signal, adapter: hangingAdapter(captured) })
		await flush()

		expect(captured.signal).toBe(own.signal)

		resetNavigationScope()
		expect(captured.signal?.aborted, "a component-owned request must survive navigation").toBe(false)

		// The owning component still gets its rejection, so existing
		// `axios.isCancel` guards and `.finally` cleanup keep working unchanged.
		own.abort()
		await expect(settlement(request)).resolves.toBe("rejected:cancel")
	})

	it("keeps `keepOnNavigation` requests unattached across a route change", async () => {
		const captured: Captured = {}
		HttpClient.get("/auth/refresh", { keepOnNavigation: true, adapter: hangingAdapter(captured) })
		await flush()

		expect(captured.signal).toBeUndefined()

		resetNavigationScope()
		expect(captured.signal).toBeUndefined()
	})

	it("gives each route a fresh scope, so the incoming page's loads are not cancelled", async () => {
		const stale: Captured = {}
		HttpClient.get("/overview/customers", { adapter: hangingAdapter(stale) })
		await flush()

		resetNavigationScope() // leave the page

		const fresh: Captured = {}
		HttpClient.get("/ai_analyst/jobs", { adapter: hangingAdapter(fresh) })
		await flush()

		expect(stale.signal?.aborted).toBe(true)
		expect(fresh.signal?.aborted, "the new page's request must not inherit the aborted scope").toBe(false)
	})
})
