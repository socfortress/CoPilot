import { flushPromises, mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { useAlertsFilters } from "../useAlertsFilters"

async function setup(url = "/alerts") {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{ path: "/alerts", component: { render: () => null } }]
	})
	await router.push(url)
	let api!: ReturnType<typeof useAlertsFilters>
	mount(
		defineComponent({
			setup() {
				api = useAlertsFilters()
				return () => h("div")
			}
		}),
		{ global: { plugins: [router] } }
	)
	return { router, api }
}

/** The filters' one store is the URL (#1245). */
describe("useAlertsFilters", () => {
	it("reads the filters from the URL", async () => {
		const { api } = await setup("/alerts?status=OPEN&tag=vip&tag=ops&from=2026-10-01")
		expect(api.filters.value).toMatchObject({ status: "OPEN", tags: ["vip", "ops"], from: "2026-10-01", to: null })
	})

	it("writes a change into the URL, replacing the history entry", async () => {
		const { router, api } = await setup("/alerts?status=OPEN")
		const push = vi.spyOn(router, "push")
		const replace = vi.spyOn(router, "replace")

		await api.setFilters({ source: "wazuh" })

		expect(router.currentRoute.value.fullPath).toBe("/alerts?status=OPEN&source=wazuh")
		expect(api.filters.value.source).toBe("wazuh")
		expect(replace).toHaveBeenCalledTimes(1)
		expect(push).not.toHaveBeenCalled()
	})

	it("keeps two quick changes: the second builds on the first, not on the URL it replaces", async () => {
		const { router, api } = await setup()

		const first = api.setFilters({ status: "CLOSED" })
		const second = api.setFilters({ source: "office365" })
		await Promise.all([first, second])
		await flushPromises()

		expect(router.currentRoute.value.query).toMatchObject({ status: "CLOSED", source: "office365" })
	})

	it("does not navigate for a change that asks nothing new", async () => {
		const { router, api } = await setup("/alerts?title=login")
		let navigations = 0
		router.afterEach(() => navigations++)

		await api.setFilters({ title: " login " })

		expect(navigations).toBe(0)
	})

	it("clears every filter and keeps the rest of the query", async () => {
		const { router, api } = await setup("/alerts?status=OPEN&tag=vip&page=2")
		await api.clearFilters()
		expect(router.currentRoute.value.query).toEqual({ page: "2" })
	})
})
