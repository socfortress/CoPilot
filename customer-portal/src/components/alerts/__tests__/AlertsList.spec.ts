import type { AlertsFilters } from "@/components/alerts/filters/alertsFilters"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, ref } from "vue"
import { EMPTY_ALERTS_FILTERS } from "@/components/alerts/filters/alertsFilters"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import AlertsList from "../List.vue"

const getFilteredAlerts = vi.hoisted(() => vi.fn())
const getAlertsFilters = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({
	default: {
		alerts: { getFilteredAlerts, getAlertsFilters, searchAlertAssets: vi.fn() }
	}
}))

function mountList(initial: Partial<AlertsFilters> = {}) {
	const filters = ref<AlertsFilters>({ ...EMPTY_ALERTS_FILTERS, ...initial })
	const changes: Partial<AlertsFilters>[] = []
	// The component under test, inside the message provider it needs.
	const content = () =>
		h(AlertsList, {
			filters: filters.value,
			onChange: (patch: Partial<AlertsFilters>) => changes.push(patch)
		})

	const wrapper = mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, content)
		}),
		// The detail and status components are not what this spec is about.
		{ global: { stubs: { AlertDetailsButton: true, AlertStatusSelect: true } } }
	)
	return { wrapper, filters, changes }
}

/** One request with every filter at once (#1245), instead of one endpoint per filter. */
describe("alerts list", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getFilteredAlerts.mockReset()
		getFilteredAlerts.mockResolvedValue({ data: { alerts: [], total: 99, total_filtered: 7 } })
		getAlertsFilters.mockResolvedValue({ data: { sources: [], tags: [], statuses: [], assets: [] } })
	})

	it("loads once, with every filter and the global customer filter", async () => {
		useCustomerFilterStore().setSelected(["ACME"])
		mountList({ status: "OPEN", tags: ["vip"], source: "wazuh" })
		await flushPromises()

		expect(getFilteredAlerts).toHaveBeenCalledTimes(1)
		const [params, pagination, signal, customers] = getFilteredAlerts.mock.calls[0]!
		expect(params).toEqual({ status: "OPEN", tags: ["vip"], source: "wazuh" })
		expect(pagination).toMatchObject({ page: 1, pageSize: 25 })
		expect(signal).toBeInstanceOf(AbortSignal)
		expect(customers).toEqual(["ACME"])
	})

	it("pages over the filtered count, not over every alert", async () => {
		const { wrapper } = mountList({ status: "OPEN" })
		await flushPromises()
		expect(wrapper.text()).toContain("7")
		expect(wrapper.text()).not.toContain("99")
	})

	it("reloads when the filters ask something new, and only then", async () => {
		const { filters } = mountList({ status: "OPEN" })
		await flushPromises()

		// A new object asking the same thing (another query key changed, say).
		filters.value = { ...filters.value }
		await flushPromises()
		expect(getFilteredAlerts).toHaveBeenCalledTimes(1)

		filters.value = { ...filters.value, status: "CLOSED" }
		await flushPromises()
		expect(getFilteredAlerts).toHaveBeenCalledTimes(2)
		expect(getFilteredAlerts.mock.calls[1]![0]).toEqual({ status: "CLOSED" })
	})

	it("offers to clear the filters when they match nothing", async () => {
		getFilteredAlerts.mockResolvedValue({ data: { alerts: [], total: 6, total_filtered: 0 } })
		const { wrapper, changes } = mountList({ source: "nowhere" })
		await flushPromises()

		await wrapper.get("[data-testid=alerts-empty-clear]").trigger("click")
		expect(changes).toEqual([EMPTY_ALERTS_FILTERS])
	})

	it("offers no clearing when nothing is filtered", async () => {
		getFilteredAlerts.mockResolvedValue({ data: { alerts: [], total: 0, total_filtered: 0 } })
		const { wrapper } = mountList()
		await flushPromises()
		await nextTick()
		expect(wrapper.find("[data-testid=alerts-empty-clear]").exists()).toBe(false)
	})
})
