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
			name === "default" ? undefined : defineComponent({ name, setup: (_p, { slots }) => () => h("div", slots.default?.()) })
	}
)

const CARDS = [
	["AgentsCard", () => import("../AgentsCard.vue")],
	["IncidentAlerts", () => import("../IncidentAlerts.vue")],
	["IncidentCases", () => import("../IncidentCases.vue")]
] as const

describe.each(CARDS)("%s — aborting on filter change", (_name, load) => {
	beforeEach(() => {
		issued.length = 0
	})

	it("aborts the in-flight request before issuing the new one", async () => {
		const { default: Card } = await load()
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
		const { default: Card } = await load()
		const wrapper = mount(Card, { props: { customerCodes: [] }, global: { stubs } })
		await flushPromises()

		const signal = issued[0].signal
		expect(signal?.aborted).toBe(false)

		wrapper.unmount()

		expect(signal?.aborted).toBe(true)
	})
})
