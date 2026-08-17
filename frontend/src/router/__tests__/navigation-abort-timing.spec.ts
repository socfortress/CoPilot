/**
 * When the outgoing page's requests are cancelled matters (#1072).
 *
 * Every route in this app is lazily loaded, so the router fetches the target's JS
 * chunk before it can complete a navigation. A browser allows ~6 concurrent
 * connections per host, and a page like Overview saturates them with requests
 * that take seconds — so the chunk request queues behind the page being left and
 * navigation appears to hang.
 *
 * The first implementation reset the scope in `afterEach`, which fires only once
 * navigation is confirmed: correct, but after the chunk had already been
 * fetched — far too late to free the connections that were blocking it. Leaving
 * Overview immediately felt instant; leaving after a second or two stalled.
 *
 * These tests pin the two properties that fix depends on: the reset happens
 * before* the route component is resolved, and a rejected navigation never
 * reaches it.
 */

import { beforeEach, describe, expect, it } from "vitest"
import { createMemoryHistory, createRouter } from "vue-router"

const events: string[] = []

/** A stand-in for a lazily loaded route component. */
function lazyComponent(name: string) {
	return () => {
		events.push(`chunk:${name}`)
		return Promise.resolve({ template: `<div>${name}</div>` })
	}
}

function buildRouter(options: { authCheckPasses?: boolean } = {}) {
	const { authCheckPasses = true } = options

	const router = createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/", component: lazyComponent("home") },
			{ path: "/login", component: lazyComponent("login") },
			{ path: "/overview", component: lazyComponent("overview") },
			{ path: "/alerts", component: lazyComponent("alerts") }
		]
	})

	// Mirrors src/router/index.ts: authCheck is registered first, the abort second.
	router.beforeEach(to => {
		events.push("authCheck")
		// `/login` itself must pass, or rejecting every navigation redirects to a
		// route that is itself rejected — an infinite redirection that hangs.
		if (authCheckPasses || to.path === "/login") return true
		return "/login"
	})
	router.beforeEach((to, from) => {
		if (to.path !== from.path) events.push("abort")
		return true
	})

	return router
}

describe("navigation-scoped abort timing", () => {
	beforeEach(() => {
		events.length = 0
	})

	it("aborts before the route chunk is requested", async () => {
		const router = buildRouter()
		await router.push("/overview")
		events.length = 0

		await router.push("/alerts")

		const abortAt = events.indexOf("abort")
		const chunkAt = events.indexOf("chunk:alerts")

		expect(abortAt).toBeGreaterThanOrEqual(0)
		expect(chunkAt).toBeGreaterThanOrEqual(0)
		// The whole fix: connections are freed before the router asks for the chunk
		// that would otherwise queue behind them.
		expect(abortAt).toBeLessThan(chunkAt)
	})

	it("never aborts a navigation the auth guard rejects", async () => {
		const router = buildRouter({ authCheckPasses: false })
		await router.push("/overview").catch(() => {})
		events.length = 0

		await router.push("/alerts").catch(() => {})

		// authCheck runs; the abort guard must not, or a redirect to /login would
		// cancel the requests of a page the user ends up staying on.
		expect(events).toContain("authCheck")
		expect(events).not.toContain("abort")
	})

	it("does not abort on a query-only change", async () => {
		const router = buildRouter()
		await router.push("/overview")
		events.length = 0

		await router.push("/overview?tab=stories")

		// Views that sync filters to the URL push a query change while their own
		// request is in flight; resetting there would cancel it.
		expect(events).not.toContain("abort")
	})

	it("aborts once per path change, not once per guard run", async () => {
		const router = buildRouter()
		await router.push("/overview")
		events.length = 0

		await router.push("/alerts")
		await router.push("/")

		expect(events.filter(e => e === "abort")).toHaveLength(2)
	})
})
