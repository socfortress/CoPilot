import type { AlertsFilters } from "../alertsFilters"
import { flushPromises, mount } from "@vue/test-utils"
import { NDatePicker, NDropdown, NInput, NMessageProvider, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, ref } from "vue"
import AlertsFilterBar from "../AlertsFilterBar.vue"
import { EMPTY_ALERTS_FILTERS } from "../alertsFilters"

const getAlertsFilters = vi.hoisted(() => vi.fn())
const searchAlertAssets = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { alerts: { getAlertsFilters, searchAlertAssets } } }))

/** The bar is controlled: it emits patches, and the test applies them as the page would. */
function mountBar(initial: Partial<AlertsFilters> = {}) {
	const filters = ref<AlertsFilters>({ ...EMPTY_ALERTS_FILTERS, ...initial })
	const patches: Partial<AlertsFilters>[] = []
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () =>
					h(AlertsFilterBar, {
						filters: filters.value,
						onChange: (patch: Partial<AlertsFilters>) => {
							patches.push(patch)
							filters.value = { ...filters.value, ...patch }
						}
					}))
		})
	)
	const group = (type: string) => wrapper.find(`[data-testid=alerts-filter-${type}]`)
	const select = (type: string) => wrapper.getComponent(`[data-testid=alerts-filter-${type}]`).findComponent(NSelect)
	const menu = () =>
		(wrapper.findComponent(NDropdown).props("options") as { key: string }[]).map(option => option.key)
	return { wrapper, filters, patches, group, select, menu }
}

describe("alertsFilterBar (#1245)", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getAlertsFilters.mockResolvedValue({
			data: { sources: ["wazuh", "office365"], tags: ["vip"], statuses: [], assets: [] }
		})
		searchAlertAssets.mockResolvedValue({ data: { assets: ["host-a1"] } })
	})

	afterEach(() => {
		vi.useRealTimers()
		vi.clearAllMocks()
	})

	it("shows a group for every filter in use, and offers the others in the menu", async () => {
		const { group, menu } = mountBar({ status: "OPEN", tags: ["vip"] })
		await flushPromises()

		expect(group("status").exists()).toBe(true)
		expect(group("tag").exists()).toBe(true)
		expect(group("source").exists()).toBe(false)
		expect(menu()).toEqual(["source", "asset", "date"])
	})

	it("shows the Activity page's filters as removable chips, never in the menu (#1284)", async () => {
		const { wrapper, group, menu, patches } = mountBar({
			detection: "Brute force",
			openedFrom: "2026-09-01T12:00:00Z",
			openedBefore: "2026-10-01T12:00:00Z"
		})
		await flushPromises()

		expect(wrapper.get("[data-testid=alerts-filter-detection-value]").text()).toBe("Brute force")
		const window = wrapper.get("[data-testid=alerts-filter-opened-value]").text()
		expect(window).toContain(" – ")
		expect(group("opened").text()).toContain("Reached the SOC")
		expect(menu()).toEqual(["status", "source", "asset", "tag", "date"])

		await wrapper.get("[data-testid=alerts-filter-opened-remove]").trigger("click")
		expect(patches.at(-1)).toMatchObject({ openedFrom: null, openedBefore: null, detection: "Brute force" })
		await nextTick()
		expect(group("opened").exists()).toBe(false)
		expect(group("detection").exists()).toBe(true)

		await wrapper.get("[data-testid=alerts-filter-clear]").trigger("click")
		expect(patches.at(-1)).toEqual(EMPTY_ALERTS_FILTERS)
	})

	it("adds an empty group from the menu, which a value turns into a filter", async () => {
		const { wrapper, group, select, patches } = mountBar()
		await flushPromises()

		wrapper.findComponent(NDropdown).vm.$emit("select", "source")
		await nextTick()
		expect(group("source").exists()).toBe(true)
		expect(patches).toEqual([])
		expect((select("source").props("options") as { value: string }[]).map(o => o.value)).toEqual([
			"wazuh",
			"office365"
		])

		select("source").vm.$emit("update:value", "office365")
		expect(patches).toEqual([{ source: "office365" }])
	})

	it("removing a group clears its filter, the date range as a whole", async () => {
		const { group, patches, wrapper } = mountBar({ source: "wazuh", from: "2026-10-01", to: "2026-10-13" })
		await flushPromises()

		await wrapper.get("[data-testid=alerts-filter-date-remove]").trigger("click")
		expect(patches.at(-1)).toMatchObject({ from: null, to: null, source: "wazuh" })
		expect(group("date").exists()).toBe(false)
	})

	it("keeps a group emptied in its own control, until its remove button", async () => {
		const { group, select, patches } = mountBar({ tags: ["vip"] })
		await flushPromises()

		select("tag").vm.$emit("update:value", [])
		await nextTick()
		expect(patches).toEqual([{ tags: [] }])
		expect(group("tag").exists()).toBe(true)
	})

	it("removing a group that was never given a value changes nothing", async () => {
		const { wrapper, group, patches } = mountBar()
		await flushPromises()
		wrapper.findComponent(NDropdown).vm.$emit("select", "asset")
		await nextTick()

		await wrapper.get("[data-testid=alerts-filter-asset-remove]").trigger("click")
		expect(group("asset").exists()).toBe(false)
		expect(patches).toEqual([])
	})

	it("searches assets on the server, and keeps showing the one selected", async () => {
		const { select } = mountBar({ asset: "host-z9" })
		await flushPromises()

		select("asset").vm.$emit("focus")
		await flushPromises()
		expect(searchAlertAssets).toHaveBeenCalledWith(null, expect.any(AbortSignal))
		expect((select("asset").props("options") as { value: string }[]).map(o => o.value)).toEqual([
			"host-a1",
			"host-z9"
		])
	})

	it("offers every status, the waiting one by the customer's name for it", async () => {
		const { select } = mountBar({ status: "OPEN" })
		await flushPromises()
		const labels = (select("status").props("options") as { label: string }[]).map(o => o.label)
		expect(labels).toEqual(["Open", "In Progress", "Waiting on you", "Closed"])
	})

	it("turns the picked days into calendar days, with an open end allowed", async () => {
		const { wrapper, patches } = mountBar({ from: "2026-10-01" })
		await flushPromises()
		const [from, to] = wrapper.findAllComponents(NDatePicker)

		expect(from!.props("value")).toBe(new Date(2026, 9, 1).getTime())
		expect(to!.props("value")).toBeNull()
		to!.vm.$emit("update:value", new Date(2026, 9, 13, 15, 0).getTime())
		from!.vm.$emit("update:value", null)
		expect(patches).toEqual([{ to: "2026-10-13" }, { from: null }])
	})

	it("debounces the title search, and applies it at once on Enter", async () => {
		vi.useFakeTimers()
		const { wrapper, patches } = mountBar()
		const input = wrapper.findComponent(NInput)

		input.vm.$emit("update:value", "log")
		input.vm.$emit("update:value", "login")
		await nextTick()
		expect(patches).toEqual([])
		await vi.advanceTimersByTimeAsync(300)
		expect(patches).toEqual([{ title: "login" }])

		input.vm.$emit("update:value", "login failed")
		await nextTick()
		await wrapper.get("[data-testid=alerts-filter-title] input").trigger("keydown", { key: "Enter" })
		expect(patches.at(-1)).toEqual({ title: "login failed" })
		// The debounced copy catching up finds nothing left to change.
		await vi.advanceTimersByTimeAsync(300)
		expect(patches).toHaveLength(2)
	})

	it("shows the title the URL says when it changes underneath (back, a link)", async () => {
		const { wrapper, filters } = mountBar({ title: "login" })
		filters.value = { ...filters.value, title: "vpn" }
		await nextTick()
		expect(wrapper.findComponent(NInput).props("value")).toBe("vpn")
	})

	it("clears everything at once, and is offered only when something is filtered", async () => {
		const { wrapper, patches } = mountBar({ title: "x", status: "OPEN" })
		await flushPromises()

		await wrapper.get("[data-testid=alerts-filter-clear]").trigger("click")
		expect(patches).toEqual([EMPTY_ALERTS_FILTERS])
		expect(wrapper.find("[data-testid=alerts-filter-status]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=alerts-filter-clear]").exists()).toBe(false)
	})
})
