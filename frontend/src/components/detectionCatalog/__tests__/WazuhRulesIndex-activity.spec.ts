import type { CatalogWazuhRulesResponse } from "@/types/detection-catalog"
import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import Api from "@/api"
import WazuhRulesIndex from "../WazuhRulesIndex.vue"

// #1319: the Activity column must not show before the hit counts are known, must
// say why it is missing, and must not show zeros for a customer whose count failed.

vi.mock("@/api", () => ({
	default: {
		detectionCatalog: { listWazuhRules: vi.fn() },
		customers: { getCustomers: vi.fn() }
	}
}))

const listWazuhRules = vi.mocked(Api.detectionCatalog.listWazuhRules)
const getCustomers = vi.mocked(Api.customers.getCustomers)

function answer(overrides: Partial<CatalogWazuhRulesResponse> = {}) {
	return {
		data: {
			success: true,
			message: "ok",
			rules: [
				{
					id: 5710,
					level: 10,
					status: "enabled",
					description: "sshd: attempt to login using a non-existent user",
					filename: "0095-sshd_rules.xml",
					relative_dirname: "ruleset/rules",
					groups: ["sshd"],
					mitre: [],
					hits_7d: 0,
					hits_30d: 0,
					last_seen: null
				}
			],
			total: 1,
			available: true,
			unavailable_reason: null,
			last_refresh: null,
			firing_stats_available: true,
			firing_stats_unavailable_reason: null,
			firing_stats_last_refresh: null,
			firing_stats_loading: false,
			customer_firing_stats_status: null,
			customer_firing_stats_error: null,
			customer_code: "",
			...overrides
		}
	} as never
}

async function render() {
	const blank = { render: () => null }
	const appRouter = createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/", component: blank },
			{ path: "/detection-catalog/wazuh-rules/:id", name: "DetectionCatalogWazuhRule", component: blank }
		]
	})
	await appRouter.push("/")
	await appRouter.isReady()
	const Host = defineComponent({
		setup: () => () =>
			h(NMessageProvider, null, {
				default: () => h(NDialogProvider, null, { default: () => h(WazuhRulesIndex) })
			})
	})
	const wrapper = mount(Host, {
		attachTo: document.body,
		global: { plugins: [appRouter], stubs: { WazuhRuleDetail: true, WazuhLogTest: true } }
	})
	await flushPromises()
	const inner = wrapper.findComponent(WazuhRulesIndex) as unknown as { vm: Record<string, unknown> }
	return { wrapper, state: inner.vm }
}

function headers(wrapper: Awaited<ReturnType<typeof render>>["wrapper"]) {
	return wrapper.findAll("th").map(th => th.text())
}

function notice(wrapper: Awaited<ReturnType<typeof render>>["wrapper"]) {
	return wrapper.find("[data-testid=activity-notice]")
}

beforeEach(() => {
	setActivePinia(createPinia())
	listWazuhRules.mockReset()
	getCustomers.mockReset()
	getCustomers.mockResolvedValue({
		data: { success: true, customers: [{ customer_code: "acme", customer_name: "Acme" }] }
	} as never)
})

afterEach(() => {
	vi.useRealTimers()
	document.body.innerHTML = ""
})

describe("the Activity column on the Wazuh Rules tab", () => {
	it("is hidden until the counts exist, says so, then appears once they land", async () => {
		vi.useFakeTimers()
		listWazuhRules
			.mockResolvedValueOnce(answer({ firing_stats_available: false, firing_stats_loading: true }))
			.mockResolvedValueOnce(answer({ firing_stats_available: false, firing_stats_loading: true }))
			.mockResolvedValueOnce(answer())
			.mockResolvedValueOnce(answer())

		const { wrapper } = await render()

		expect(headers(wrapper)).not.toContain("Activity")
		expect(notice(wrapper).text()).toContain("Counting rule hits")

		// Still counting: asks again, cheaply.
		await vi.advanceTimersByTimeAsync(5000)
		expect(listWazuhRules).toHaveBeenCalledTimes(2)
		expect(listWazuhRules.mock.calls[1][0]).toMatchObject({ limit: 1 })
		expect(headers(wrapper)).not.toContain("Activity")

		// Landed: one full read, and the column is there.
		await vi.advanceTimersByTimeAsync(5000)
		await flushPromises()
		expect(listWazuhRules).toHaveBeenCalledTimes(4)
		expect(listWazuhRules.mock.calls[3][0]).not.toHaveProperty("limit")
		expect(headers(wrapper)).toContain("Activity")
		expect(notice(wrapper).exists()).toBe(false)

		// Settled: no more asking.
		await vi.advanceTimersByTimeAsync(30000)
		expect(listWazuhRules).toHaveBeenCalledTimes(4)
	})

	it("says nothing about the counts before anything was asked", async () => {
		// The customer list is read first; seen live, the tab called the counts
		// "unavailable" during that wait.
		getCustomers.mockReturnValue(new Promise(() => {}) as never)

		const { wrapper } = await render()

		expect(listWazuhRules).not.toHaveBeenCalled()
		expect(notice(wrapper).exists()).toBe(false)
	})

	it("shows the indexer's reason when the counts are unavailable", async () => {
		listWazuhRules.mockResolvedValue(
			answer({
				firing_stats_available: false,
				firing_stats_unavailable_reason:
					"Counting rule hits did not finish within 120s. Raise FIRING_STATS_TIMEOUT_SECONDS."
			})
		)

		const { wrapper } = await render()

		expect(headers(wrapper)).not.toContain("Activity")
		expect(notice(wrapper).text()).toContain("Rule hit counts unavailable")
		expect(notice(wrapper).text()).toContain("did not finish within 120s")
		expect(wrapper.text()).not.toContain("Top noisy")
	})

	it("flags a customer whose count failed instead of showing zeros, and keeps the scope selector", async () => {
		listWazuhRules
			.mockResolvedValueOnce(answer())
			.mockResolvedValueOnce(
				answer({
					customer_code: "acme",
					customer_firing_stats_status: "error",
					customer_firing_stats_error: "Wazuh indexer is not reachable."
				})
			)

		const { wrapper, state } = await render()
		expect(headers(wrapper)).toContain("Activity")
		;(state.onCustomerChange as (code: string) => void)("acme")
		await flushPromises()

		expect(listWazuhRules.mock.calls[1][0]).toMatchObject({ customerCode: "acme" })
		expect(headers(wrapper)).not.toContain("Activity")
		expect(wrapper.text()).not.toContain("No hits 30d")
		expect(notice(wrapper).text()).toContain("Hit counts for Acme (acme) unavailable")
		expect(notice(wrapper).text()).toContain("Wazuh indexer is not reachable.")
		expect(wrapper.find(".n-select").exists()).toBe(true)
	})
})
