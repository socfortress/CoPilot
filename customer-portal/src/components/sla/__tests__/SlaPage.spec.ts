import type { SlaOverview } from "@/types/sla"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import SlaPage from "../SlaPage.vue"
import { useSlaOverview } from "../useSlaOverview"

const getOverview = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { sla: { getOverview } } }))
vi.mock("vue-echarts", () => ({
	default: defineComponent({ name: "VChart", props: { option: Object }, setup: () => () => h("div") })
}))

const RouterLinkStub = defineComponent({
	props: { to: { type: Object, required: true } },
	setup: (_, { slots }) => () => h("a", slots.default?.())
})

function overview(overrides: Partial<SlaOverview> = {}): SlaOverview {
	const entity = {
		opened: 6,
		resolved: 2,
		acknowledge: { met: 5, breached: 1, rate: 83.3 },
		resolve: { met: 2, breached: 0, rate: 100 },
		time_to_acknowledge: 600,
		time_to_resolve: 10_800
	}
	return {
		enabled: true,
		customer_codes: ["ACME"],
		date_from: "2026-09-01T00:00:00",
		date_to: "2026-10-01T00:00:00",
		bucket: "day",
		tracking_since: null,
		alerts: entity,
		cases: entity,
		previous_alerts: null,
		previous_cases: null,
		targets: [
			{
				entity: "alert",
				severity: "High",
				acknowledge_minutes: 60,
				resolve_minutes: 480,
				business_hours: false,
				opened: 6,
				acknowledge_rate: 83.3,
				resolve_rate: 100,
				time_to_resolve: 10_800
			}
		],
		trend: [{ start: "2026-09-01T00:00:00", opened: 6, resolved: 2, rate: 100 }],
		open_now: { alerts: 5, cases: 2, breached: 0, at_risk: 1, waiting_on_you: 2 },
		...overrides
	}
}

function respond(value: SlaOverview) {
	return Promise.resolve({ data: value })
}

function mountPage() {
	return mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(SlaPage)) }),
		{ global: { stubs: { RouterLink: RouterLinkStub } } }
	)
}

beforeEach(() => {
	setActivePinia(createPinia())
	getOverview.mockReset()
})

describe("slaPage (#1187)", () => {
	it("shows skeletons while the first figures load, then the figures", async () => {
		let resolve: (value: unknown) => void = () => {}
		getOverview.mockImplementation(() => new Promise(r => (resolve = r)))
		const wrapper = mountPage()
		expect(wrapper.find("[data-testid^=sla-kpi-]").exists()).toBe(false)
		expect(wrapper.find(".n-skeleton").exists()).toBe(true)

		resolve({ data: overview() })
		await flushPromises()
		expect(wrapper.findAll("[data-testid^=sla-kpi-alert-], [data-testid^=sla-kpi-case-]")).toHaveLength(4)
		expect(wrapper.find("[data-testid=sla-open-now]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=sla-target-alert-high]").exists()).toBe(true)
	})

	it("says the page is not published instead of showing empty figures", async () => {
		getOverview.mockImplementation(() =>
			respond(overview({ enabled: false, alerts: null, cases: null, open_now: null, targets: [], trend: [] }))
		)
		const wrapper = mountPage()
		await flushPromises()
		expect(wrapper.find("[data-testid=sla-disabled]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=sla-open-now]").exists()).toBe(false)
	})

	it("shows a failed first load with a retry that loads again", async () => {
		getOverview.mockImplementationOnce(() => Promise.reject(new Error("network down")))
		getOverview.mockImplementationOnce(() => respond(overview()))
		const wrapper = mountPage()
		await flushPromises()
		expect(wrapper.text()).toContain("network down")

		await wrapper.get("button").trigger("click")
		await flushPromises()
		expect(getOverview).toHaveBeenCalledTimes(2)
		expect(wrapper.text()).not.toContain("network down")
		expect(wrapper.find("[data-testid=sla-open-now]").exists()).toBe(true)
	})

	it("keeps the figures on screen when a refresh fails, and says so", async () => {
		getOverview.mockImplementationOnce(() => respond(overview()))
		getOverview.mockImplementationOnce(() => Promise.reject(new Error("timeout")))
		const wrapper = mountPage()
		await flushPromises()
		await wrapper.get("[data-testid=sla-period-7d] input").setValue(true)
		await flushPromises()
		expect(wrapper.get("[data-testid=sla-refresh-error]").text()).toContain("timeout")
		expect(wrapper.find("[data-testid=sla-open-now]").exists()).toBe(true)
	})

	it("says an empty period is empty rather than drawing zeros", async () => {
		const quiet = { ...overview().alerts!, opened: 0, resolved: 0 }
		getOverview.mockImplementation(() => respond(overview({ alerts: quiet, cases: quiet, trend: [] })))
		const wrapper = mountPage()
		await flushPromises()
		expect(wrapper.get("[data-testid=sla-trend]").text()).toContain("Nothing tracked was opened or resolved")
	})

	it("reloads for another period, over that many days", async () => {
		getOverview.mockImplementation(() => respond(overview()))
		const wrapper = mountPage()
		await flushPromises()
		await wrapper.get("[data-testid=sla-period-7d] input").setValue(true)
		await flushPromises()
		expect(getOverview).toHaveBeenCalledTimes(2)
		const [from, to] = getOverview.mock.calls[1] as [Date, Date]
		expect(to.getTime() - from.getTime()).toBe(7 * 86_400_000)
	})

	it("passes the global customer filter, and reloads when it changes", async () => {
		getOverview.mockImplementation(() => respond(overview()))
		mountPage()
		await flushPromises()
		expect(getOverview.mock.calls[0]![2]).toBeUndefined() // nothing selected: every accessible customer

		useCustomerFilterStore().setSelected(["ACME"])
		await flushPromises()
		expect(getOverview).toHaveBeenCalledTimes(2)
		expect(getOverview.mock.calls[1]![2]).toEqual(["ACME"])
	})
})

describe("useSlaOverview (#1187)", () => {
	function host() {
		const period = ref<"7d" | "30d" | "90d">("30d")
		let state!: ReturnType<typeof useSlaOverview>
		const wrapper = mount(
			defineComponent({
				setup() {
					state = useSlaOverview(period)
					return () => h("div")
				}
			})
		)
		return { wrapper, period, state: () => state }
	}

	it("lets only the latest load count, and aborts the one it replaces", async () => {
		const pending: { resolve: (value: unknown) => void; signal: AbortSignal }[] = []
		getOverview.mockImplementation(
			(_from: Date, _to: Date, _codes: unknown, signal: AbortSignal) =>
				new Promise(resolve => pending.push({ resolve, signal }))
		)
		const { period, state } = host()
		period.value = "7d"
		await flushPromises()
		expect(pending).toHaveLength(2)
		expect(pending[0]!.signal.aborted).toBe(true)

		pending[1]!.resolve({ data: overview({ customer_codes: ["NEW"] }) })
		pending[0]!.resolve({ data: overview({ customer_codes: ["STALE"] }) })
		await flushPromises()
		expect(state().overview.value?.customer_codes).toEqual(["NEW"])
		expect(state().loading.value).toBe(false)
	})

	it("aborts its load when the page goes away", async () => {
		let signal: AbortSignal | undefined
		getOverview.mockImplementation((_f: Date, _t: Date, _c: unknown, s: AbortSignal) => {
			signal = s
			return new Promise(() => {})
		})
		const { wrapper } = host()
		await flushPromises()
		wrapper.unmount()
		expect(signal?.aborted).toBe(true)
	})

	it("reports a failure as a message and clears it on the next success", async () => {
		getOverview.mockImplementationOnce(() => Promise.reject(new Error("boom")))
		getOverview.mockImplementationOnce(() => respond(overview()))
		const { state } = host()
		await flushPromises()
		expect(state().error.value).toContain("boom")

		await state().reload()
		expect(state().error.value).toBeNull()
		expect(state().overview.value?.enabled).toBe(true)
	})
})
