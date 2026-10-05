import type { Ref } from "vue"
import type { SocDashboardQuery } from "@/api/endpoints/soc-management"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, shallowRef } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { dashboardKey, useSocDashboard } from "../composables/useSocDashboard"
import { useSocFilters } from "../composables/useSocFilters"

const getDashboard = vi.fn()
vi.mock("@/api", () => ({
	default: { socManagement: { getDashboard: (...args: unknown[]) => getDashboard(...args) } }
}))

async function withFilters(path: string) {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{ path: "/soc-management", component: { render: () => null } }]
	})
	await router.push(path)
	await router.isReady()
	let filters!: ReturnType<typeof useSocFilters>
	mount(
		defineComponent({
			setup() {
				filters = useSocFilters()
				return () => h("div")
			}
		}),
		{ global: { plugins: [router] } }
	)
	return { filters, router }
}

describe("useSocFilters (state in the URL)", () => {
	beforeEach(() => {
		vi.useFakeTimers()
		vi.setSystemTime(new Date("2026-09-30T10:15:42Z"))
	})
	afterEach(() => vi.useRealTimers())

	it("defaults to the overview tab and a 30-day rolling window", async () => {
		const { filters } = await withFilters("/soc-management")
		expect(filters.tab.value).toBe("overview")
		expect(filters.preset.value).toBe("30d")
		expect(filters.range.value.to.toISOString()).toBe("2026-09-30T10:16:00.000Z")
		expect(filters.range.value.from.toISOString()).toBe("2026-08-31T10:16:00.000Z")
	})

	it("reads tab, period, customers, severities and sources from the query", async () => {
		const { filters } = await withFilters(
			"/soc-management?tab=rules&period=7d&customer=ACME&customer=GLOBEX&severity=High&severity=Bogus&source=wazuh"
		)
		expect(filters.tab.value).toBe("rules")
		expect(filters.preset.value).toBe("7d")
		expect(filters.customerCodes.value).toEqual(["ACME", "GLOBEX"])
		expect(filters.severities.value).toEqual(["High"]) // an unknown severity is dropped, not sent
		expect(filters.sources.value).toEqual(["wazuh"])
		expect(filters.hasCustomerInUrl.value).toBe(true)
	})

	it("ignores an unknown tab and a custom period without a valid range", async () => {
		const { filters } = await withFilters("/soc-management?tab=nope&period=custom&from=garbage")
		expect(filters.tab.value).toBe("overview")
		expect(filters.preset.value).toBe("30d")
	})

	it("keeps every change made in one go, though the URL has not caught up between them", async () => {
		const { filters, router } = await withFilters("/soc-management?tab=customers")
		filters.customerCodes.value = ["ACME"]
		filters.tab.value = "overview"
		await flushPromises()
		expect(router.currentRoute.value.query.tab).toBe("overview")
		expect([router.currentRoute.value.query.customer].flat()).toEqual(["ACME"])
	})

	it("writes changes back to the URL with replace, keeping the other params", async () => {
		const { filters, router } = await withFilters("/soc-management?tab=sla")
		const replace = vi.spyOn(router, "replace")
		filters.customerCodes.value = ["ACME"]
		await flushPromises()
		expect(replace).toHaveBeenCalled()
		expect(router.currentRoute.value.query).toMatchObject({ tab: "sla", customer: ["ACME"] })

		filters.setCustomRange({ from: new Date("2026-09-01T00:00:00Z"), to: new Date("2026-09-15T00:00:00Z") })
		await flushPromises()
		expect(filters.preset.value).toBe("custom")
		expect(filters.range.value.from.toISOString()).toBe("2026-09-01T00:00:00.000Z")

		filters.preset.value = "24h"
		await flushPromises()
		expect(router.currentRoute.value.query.from).toBeUndefined()
		expect(filters.query.value.customerCodes).toEqual(["ACME"])
	})

	it("refuses a custom range the backend would reject", async () => {
		const { filters } = await withFilters("/soc-management")
		filters.setCustomRange({ from: new Date("2025-01-01T00:00:00Z"), to: new Date("2026-09-01T00:00:00Z") })
		await flushPromises()
		expect(filters.preset.value).toBe("30d")
	})
})

describe("useSocDashboard (one snapshot per change of filters)", () => {
	const base: SocDashboardQuery = {
		dateFrom: new Date("2026-09-01T00:00:00Z"),
		dateTo: new Date("2026-10-01T00:00:00Z")
	}

	beforeEach(() => {
		// A block body: a function returned from beforeEach would be run as a teardown.
		getDashboard.mockReset()
	})

	function host(query: Ref<SocDashboardQuery>) {
		let state!: ReturnType<typeof useSocDashboard>
		mount(
			defineComponent({
				setup() {
					state = useSocDashboard(query)
					return () => h("div")
				}
			})
		)
		return state
	}

	it("keys a query by value, order-insensitively", () => {
		const a = dashboardKey({ ...base, customerCodes: ["B", "A"] })
		const b = dashboardKey({ ...base, dateFrom: new Date(base.dateFrom), customerCodes: ["A", "B"] })
		expect(a).toBe(b)
		expect(dashboardKey({ ...base, severities: ["High"] })).not.toBe(a)
	})

	it("loads once, and a newer load aborts and outranks the one in flight", async () => {
		const resolvers: ((value: unknown) => void)[] = []
		getDashboard.mockImplementation(() => new Promise(resolve => resolvers.push(resolve)))
		const query = shallowRef<SocDashboardQuery>(base)
		const state = host(query)
		expect(getDashboard).toHaveBeenCalledTimes(1)
		const firstSignal = getDashboard.mock.calls[0][1] as AbortSignal

		query.value = { ...base, severities: ["Critical"] }
		await nextTick()
		expect(getDashboard).toHaveBeenCalledTimes(2)
		expect(firstSignal.aborted).toBe(true)

		resolvers[1]({ data: { marker: "newer" } })
		await flushPromises()
		resolvers[0]({ data: { marker: "stale" } })
		await flushPromises()
		expect((state.dashboard.value as unknown as { marker: string }).marker).toBe("newer")
		expect(state.loading.value).toBe(false)
	})

	it("does not refetch for the same filters, and reports a failure", async () => {
		getDashboard.mockImplementation(() => Promise.reject(Object.assign(new Error("boom"), { name: "AxiosError" })))
		const query = shallowRef<SocDashboardQuery>(base)
		const state = host(query)
		query.value = { ...base, dateFrom: new Date(base.dateFrom) }
		await flushPromises()
		expect(getDashboard).toHaveBeenCalledTimes(1)
		expect(state.error.value).toBeTruthy()
	})

	it("treats an aborted request as no error", async () => {
		getDashboard.mockImplementation(() =>
			Promise.reject(Object.assign(new Error("canceled"), { name: "CanceledError" }))
		)
		const state = host(shallowRef<SocDashboardQuery>(base))
		await flushPromises()
		expect(state.error.value).toBeNull()
	})
})
