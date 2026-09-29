/**
 * Navigation-scoped request cancellation: leaving a page aborts its reads.
 *
 * Each test asserts on the signal the adapter actually received: a promise that
 * merely stays pending cannot tell "aborted and swallowed" from "never aborted".
 */

import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios"
import axios from "axios"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { createMemoryHistory } from "vue-router"

vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({ userToken: null, refreshToken: vi.fn() })
}))

const { HttpClient } = await import("../httpClient")
const { anySignal, resetNavigationScope } = await import("../navigation-abort")

interface Captured {
	signal?: AbortSignal
}

/** Never answers, so the request stays in flight; records the signal it was given. */
function hangingAdapter(captured: Captured): AxiosAdapter {
	return (config: InternalAxiosRequestConfig) => {
		const signal = config.signal as AbortSignal | undefined
		captured.signal = signal
		return new Promise<never>((_resolve, reject) => {
			signal?.addEventListener("abort", () => {
				// What axios throws on abort, so `axios.isCancel` holds.
				reject(Object.assign(new Error("canceled"), { code: "ERR_CANCELED", config, __CANCEL__: true }))
			})
		})
	}
}

/** Let the interceptor chain run: it spans several microtasks before the adapter. */
function flush() {
	return new Promise(resolve => setTimeout(resolve, 0))
}

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
		resetNavigationScope()
	})

	it("aborts an in-flight GET when the route changes, without surfacing an error", async () => {
		const captured: Captured = {}
		const request = HttpClient.get("/customer_portal/overview", { adapter: hangingAdapter(captured) })
		await flush()
		expect(captured.signal?.aborted).toBe(false)

		resetNavigationScope()

		expect(captured.signal?.aborted).toBe(true)
		// Never settles: no error toast, no state update on a page that is gone.
		await expect(settlement(request)).resolves.toBe("pending")
	})

	it("also aborts a GET that brought its own signal — the portal lists never abort theirs on unmount", async () => {
		const own = new AbortController()
		const captured: Captured = {}
		const request = HttpClient.get("/incidents/db_operations/alerts", {
			signal: own.signal,
			adapter: hangingAdapter(captured)
		})
		await flush()

		resetNavigationScope()

		expect(captured.signal?.aborted).toBe(true)
		expect(own.signal.aborted, "the caller's controller is left alone").toBe(false)
		await expect(settlement(request)).resolves.toBe("pending")
	})

	it("still rejects when the caller cancels its own request (a superseded load)", async () => {
		const own = new AbortController()
		const captured: Captured = {}
		const request = HttpClient.get("/customer_portal/agents", { signal: own.signal, adapter: hangingAdapter(captured) })
		await flush()

		own.abort()

		expect(captured.signal?.aborted).toBe(true)
		await expect(settlement(request)).resolves.toBe("rejected:cancel")
	})

	it("leaves mutations alone: aborting one would only hide whether it happened", async () => {
		const captured: Captured = {}
		HttpClient.post("/incidents/db_operations/case/create", {}, { adapter: hangingAdapter(captured) })
		await flush()

		resetNavigationScope()
		expect(captured.signal).toBeUndefined()
	})

	it("leaves `keepOnNavigation` requests alone", async () => {
		const captured: Captured = {}
		HttpClient.get("/customer_portal/settings/effective", { keepOnNavigation: true, adapter: hangingAdapter(captured) })
		await flush()

		resetNavigationScope()
		expect(captured.signal).toBeUndefined()
	})

	it("gives each route a fresh scope, so the incoming page's loads are not cancelled", async () => {
		const stale: Captured = {}
		HttpClient.get("/customer_portal/overview", { adapter: hangingAdapter(stale) })
		await flush()

		resetNavigationScope()

		const fresh: Captured = {}
		HttpClient.get("/customer_portal/dashboard/alert-stats", { adapter: hangingAdapter(fresh) })
		await flush()

		expect(stale.signal?.aborted).toBe(true)
		expect(fresh.signal?.aborted).toBe(false)
	})

	it("anySignal follows every source, including one already aborted", () => {
		const a = new AbortController()
		const b = new AbortController()
		const combined = anySignal([a.signal, b.signal])
		expect(combined.aborted).toBe(false)
		b.abort()
		expect(combined.aborted).toBe(true)

		const done = new AbortController()
		done.abort()
		expect(anySignal([done.signal, new AbortController().signal]).aborted).toBe(true)
	})
})

describe("app-wide requests survive navigation", () => {
	beforeEach(() => {
		resetNavigationScope()
	})

	async function survives(call: () => Promise<unknown>) {
		const captured: Captured = {}
		const adapter = HttpClient.defaults.adapter
		HttpClient.defaults.adapter = hangingAdapter(captured)
		try {
			call().catch(() => {})
			await flush()
			resetNavigationScope()
			return captured.signal?.aborted !== true
		} finally {
			HttpClient.defaults.adapter = adapter
		}
	}

	it("branding, token refresh, AI availability, the report poller and downloads", async () => {
		const { default: Api } = await import("@/api")
		expect(await survives(() => Api.portal.getSettings())).toBe(true)
		expect(await survives(() => Api.portal.getEffectiveSettings())).toBe(true)
		expect(await survives(() => Api.auth.refresh())).toBe(true)
		expect(await survives(() => Api.aiReports.getAvailability("A"))).toBe(true)
		expect(await survives(() => Api.reports.listReports(undefined, true))).toBe(true)
		expect(await survives(() => Api.reports.downloadReport(1))).toBe(true)
		expect(await survives(() => Api.cases.downloadCaseFile(1, "x.txt"))).toBe(true)
		expect(await survives(() => Api.agents.exportAgents({}))).toBe(true)
		// ...while a page read does not.
		expect(await survives(() => Api.reports.listReports())).toBe(false)
	})
})

describe("router wiring", () => {
	it("resets the scope on a path change, before the route chunk loads, never on a query change", async () => {
		const events: string[] = []
		const lazy = (name: string) => () => {
			events.push(`chunk:${name}`)
			return Promise.resolve({ template: `<div>${name}</div>` })
		}
		vi.resetModules()
		vi.doMock("@/api/navigation-abort", () => ({ resetNavigationScope: () => events.push("abort") }))
		vi.doMock("@/utils/auth", () => ({ authCheck: () => true }))
		vi.doMock("vue-router", async importOriginal => {
			const original = await importOriginal<typeof import("vue-router")>()
			return { ...original, createWebHistory: () => createMemoryHistory() }
		})
		const { default: router } = await import("@/router")
		router.addRoute({ path: "/a", component: lazy("a") })
		router.addRoute({ path: "/b", component: lazy("b") })

		await router.push("/a")
		events.length = 0
		await router.push("/b")
		expect(events).toEqual(["abort", "chunk:b"])

		events.length = 0
		await router.push("/b?page=2")
		expect(events).toEqual([])

		vi.doUnmock("@/api/navigation-abort")
		vi.doUnmock("@/utils/auth")
		vi.doUnmock("vue-router")
	})
})
