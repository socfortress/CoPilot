/**
 * The sidebar healthcheck indicator and the toolbar notification bell are fed by
 * this store's polling, and both live *across* navigation — they are not
 * page-scoped. The router's navigation scope (#1072) must therefore never take
 * their requests over, or changing page would kill the poll and blank the
 * indicator until the next interval tick.
 *
 * The guarantee is structural: a caller-supplied signal always wins over the
 * navigation scope. These tests pin the store actually supplying one.
 */

import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"

const captured: Record<string, AbortSignal | undefined> = {}

function ok(name: string) {
	return (...args: unknown[]) => {
		captured[name] = args.find(arg => arg instanceof AbortSignal) as AbortSignal | undefined
		return Promise.resolve({ data: { success: false } })
	}
}

vi.mock("@/api", () => ({
	default: {
		graylog: { getMetrics: ok("getMetrics") },
		wazuh: { indices: { getClusterHealth: ok("getClusterHealth") } },
		healthchecks: { getHealthchecks: ok("getHealthchecks") }
	}
}))

const { useHealthcheckStore } = await import("../healthcheck")
const { resetNavigationScope } = await import("@/api/navigation-abort")

describe("healthcheck polling survives navigation", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetNavigationScope()
	})

	it.each([
		["getGraylogCheck", "getMetrics"],
		["getClusterHealth", "getClusterHealth"],
		["getHealthchecks", "getHealthchecks"]
	])("%s passes its own signal, unaffected by a route change", async (action, endpoint) => {
		const store = useHealthcheckStore()
		;(store as unknown as Record<string, () => void>)[action]()

		const signal = captured[endpoint]
		expect(signal, "the poll must supply its own signal to opt out of the navigation scope").toBeInstanceOf(
			AbortSignal
		)
		expect(signal?.aborted).toBe(false)

		resetNavigationScope() // the user changes page

		expect(signal?.aborted, "navigating must not cancel the sidebar/notifications poll").toBe(false)
	})

	it("stop() cancels the poll and lets a later start() work again", async () => {
		const store = useHealthcheckStore()

		store.getHealthchecks()
		const first = captured.getHealthchecks
		expect(first?.aborted).toBe(false)

		store.stop()
		expect(first?.aborted, "stop() should drop a poll still in flight").toBe(true)

		// A fresh controller must be armed, otherwise every later poll would be
		// born already-aborted and the indicator would never recover.
		store.getHealthchecks()
		const second = captured.getHealthchecks
		expect(second).not.toBe(first)
		expect(second?.aborted).toBe(false)
	})
})
