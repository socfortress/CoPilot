/**
 * Toggling "Use Global Customer Filter" must cancel the request it supersedes (#1072).
 *
 * The three Overview cards watch their `customerCodes` prop and refetch when it
 * changes. Without an abort, the previous request stays in flight and the two
 * answers race: the slower one wins, so the card can end up showing the filter
 * state the user just left.
 *
 * Mounted for real rather than asserted on the source, because the property
 * under test is a *timing* one — that the previous signal is aborted before the
 * next request is issued — and only running the component shows that.
 */

import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"

/** Every call records the signal it was handed and never settles. */
const issued: { signal?: AbortSignal }[] = []

function pendingRequest(config?: AbortSignal) {
	issued.push({ signal: config })
	return new Promise(() => {})
}

vi.mock("@/api", () => ({
	default: {
		agents: { getAgents: (_q: unknown, signal?: AbortSignal) => pendingRequest(signal) },
		incidentManagement: {
			alerts: { getAlertsList: (_q: unknown, signal?: AbortSignal) => pendingRequest(signal) },
			cases: { getCasesList: (_q: unknown, signal?: AbortSignal) => pendingRequest(signal) }
		}
	}
}))

vi.mock("naive-ui", async importOriginal => {
	const actual = await importOriginal<Record<string, unknown>>()
	return { ...actual, useMessage: () => ({ error: vi.fn(), warning: vi.fn(), success: vi.fn(), info: vi.fn() }) }
})

// The cards render Naive UI pieces and an icon component; none of that is what
// these tests are about, so they are reduced to inert stubs.
const stubs = new Proxy(
	{},
	{
		get: (_target, name: string) =>
			name === "default"
				? undefined
				: defineComponent({
						name,
						setup:
							(_p, { slots }) =>
							() =>
								h("div", slots.default?.())
					})
	}
)

// Resolved at module scope, not inside the tests. Awaiting the import in a test
// body puts Vite's first single-file-component transform on the test's clock —
// measured at ~1.5s for the first card — which intermittently blew the default
// 5s timeout on a loaded machine. Worse, a card whose test times out is never
// unmounted, so it keeps writing into `issued` and the *next* describe block
// fails with a count it never produced. One slow import looked like three
// unrelated failures.
const CARDS = [
	["AgentsCard", (await import("../AgentsCard.vue")).default],
	["IncidentAlerts", (await import("../IncidentAlerts.vue")).default],
	["IncidentCases", (await import("../IncidentCases.vue")).default]
] as const

describe.each(CARDS)("%s — aborting on filter change", (_name, Card) => {
	beforeEach(() => {
		issued.length = 0
	})

	it("aborts the in-flight request before issuing the new one", async () => {
		const wrapper = mount(Card, { props: { customerCodes: [] }, global: { stubs } })
		await flushPromises()

		expect(issued).toHaveLength(1)
		const first = issued[0].signal
		expect(first, "the card must pass a signal at all").toBeInstanceOf(AbortSignal)
		expect(first?.aborted).toBe(false)

		// What the switch does: the prop changes, the watcher refetches.
		await wrapper.setProps({ customerCodes: ["SOC01"] })
		await flushPromises()

		expect(issued).toHaveLength(2)
		expect(first?.aborted, "the superseded request must be cancelled").toBe(true)
		expect(issued[1].signal?.aborted, "the new request must not be").toBe(false)

		wrapper.unmount()
	})

	it("aborts on unmount, so leaving the page does not leave work running", async () => {
		const wrapper = mount(Card, { props: { customerCodes: [] }, global: { stubs } })
		await flushPromises()

		const signal = issued[0].signal
		expect(signal?.aborted).toBe(false)

		wrapper.unmount()

		expect(signal?.aborted).toBe(true)
	})
})
