import type { OverviewTrend, OverviewTrendRange } from "@/types/portal"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import OverviewTrendPanel from "../OverviewTrendPanel.vue"
import { trendDays } from "../trend"
import { useOverviewTrend } from "../useOverviewTrend"

const overviewTrend = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { portal: { overviewTrend } } }))
vi.mock("vue-echarts", () => ({
	default: defineComponent({
		name: "VChart",
		props: { option: Object },
		setup: (_, { attrs }) => () => h("div", { "data-testid": attrs["data-testid"] })
	})
}))

function trend(overrides: Partial<OverviewTrend> = {}): OverviewTrend {
	return {
		range: "7d",
		since: "2026-10-09T10:00:00Z",
		until: "2026-10-17T10:00:00Z",
		hours: [
			{ hour: "2026-10-15T10:00:00Z", alerts_opened: 4, alerts_closed: 1, cases_opened: 0, cases_closed: 2 },
			{ hour: "2026-10-16T10:00:00Z", alerts_opened: 1, alerts_closed: 1, cases_opened: 0, cases_closed: 0 }
		],
		alerts_open_at_since: 3,
		cases_open_at_since: 2,
		alerts_error: null,
		cases_error: null,
		...overrides
	}
}

function mountPanel(props: { trend?: OverviewTrend | null; loading?: boolean; error?: string | null } = {}) {
	const value = props.trend === undefined ? trend() : props.trend
	return mount(OverviewTrendPanel, {
		props: {
			trend: value,
			days: value ? trendDays(value) : null,
			range: (value?.range ?? "30d") as OverviewTrendRange,
			loading: props.loading ?? false,
			error: props.error ?? null
		},
		global: { stubs: { RouterLink: true } }
	})
}

function figure(wrapper: ReturnType<typeof mountPanel>, key: string) {
  return wrapper.get(`[data-testid=overview-trend-${key}]`).text()
}

beforeEach(() => {
	setActivePinia(createPinia())
	overviewTrend.mockReset()
})

describe("overviewTrendPanel (#1273)", () => {
	it("leads with what is still open, then how the period moved it, then what arrived and was closed", () => {
		const wrapper = mountPanel()
		// 3 open at the start, +4 −1 on the 15th, +1 −1 on the 16th.
		expect(figure(wrapper, "open")).toBe("6")
		expect(figure(wrapper, "open-caption")).toBe("still open · was 3")
		expect([figure(wrapper, "net"), figure(wrapper, "opened"), figure(wrapper, "closed")]).toEqual(["+3", "5", "2"])
		expect(wrapper.get("[data-testid=overview-trend-net]").classes()).toContain("text-warning")
		expect(figure(wrapper, "peak")).toBe("6")
		expect(wrapper.find("[data-testid=overview-trend-chart]").exists()).toBe(true)
		expect(wrapper.text()).toContain("last 7 days")
	})

	it("switches to cases: more closed than opened is a negative Net, and still never below zero open", async () => {
		const wrapper = mountPanel()
		await wrapper.get("[data-testid=overview-trend-entity-cases] input").setValue(true)
		expect([figure(wrapper, "net"), figure(wrapper, "opened"), figure(wrapper, "closed")]).toEqual(["\u22122", "0", "2"])
		expect(wrapper.get("[data-testid=overview-trend-net]").classes()).toContain("text-success")
		expect(figure(wrapper, "open")).toBe("0")
		expect(figure(wrapper, "open-caption")).toBe("all cleared · was 2")
	})

	it("has a table of every day for screen readers, with what was still open at its end", () => {
		const rows = mountPanel().findAll("[data-testid=overview-trend-table] tbody tr")
		expect(rows).toHaveLength(7)
		expect(rows.at(0)!.findAll("td").map(cell => cell.text())).toEqual(["3", "0", "0"])
		expect(rows.at(-3)!.findAll("td").map(cell => cell.text())).toEqual(["6", "4", "1"])
	})

	it("says a quiet period is quiet rather than drawing flat lines", () => {
		const wrapper = mountPanel({ trend: trend({ hours: [], alerts_open_at_since: 0 }) })
		expect(wrapper.get("[data-testid=overview-trend-empty]").text()).toContain(
			"No alerts opened, closed or still open in the last 7 days"
		)
		expect(wrapper.find("[data-testid=overview-trend-chart]").exists()).toBe(false)
	})

	it("still draws a period where nothing moved but some were waiting", () => {
		const wrapper = mountPanel({ trend: trend({ hours: [], alerts_open_at_since: 4 }) })
		expect(wrapper.find("[data-testid=overview-trend-empty]").exists()).toBe(false)
		expect(figure(wrapper, "open")).toBe("4")
		expect(figure(wrapper, "net")).toBe("0")
	})

	it("says not known rather than guessing when the start was not answered", () => {
		const wrapper = mountPanel({ trend: trend({ alerts_open_at_since: null }) })
		expect(figure(wrapper, "open")).toBe("—")
		expect(figure(wrapper, "open-caption")).toBe("not known")
		expect(figure(wrapper, "peak")).toBe("—")
		expect(figure(wrapper, "net")).toBe("+3")
	})

	it("shows one entity's failure on that entity only", async () => {
		const wrapper = mountPanel({ trend: trend({ alerts_error: "Failed to load the alert trend" }) })
		expect(wrapper.get("[data-testid=panel-error]").text()).toContain("Failed to load the alert trend")
		expect(wrapper.find("[data-testid=overview-trend-totals]").exists()).toBe(false)

		await wrapper.get("[data-testid=overview-trend-entity-cases] input").setValue(true)
		expect(wrapper.find("[data-testid=panel-error]").exists()).toBe(false)
		expect(figure(wrapper, "closed")).toBe("2")
	})

	it("shows a failed first load with a retry", async () => {
		const wrapper = mountPanel({ trend: null, error: "network down" })
		expect(wrapper.get("[data-testid=panel-error]").text()).toContain("network down")
		await wrapper.get("[data-testid=panel-error] button").trigger("click")
		expect(wrapper.emitted("retry")).toHaveLength(1)
	})

	it("keeps the days on screen, dimmed, while the next ones load", () => {
		const wrapper = mountPanel({ loading: true, error: "timeout" })
		expect(figure(wrapper, "opened")).toBe("5")
		expect(wrapper.find("[aria-busy=true]").exists()).toBe(true)
	})

	it("asks for the other period", async () => {
		const wrapper = mountPanel()
		await wrapper.get("[data-testid=overview-trend-range-30d] input").setValue(true)
		expect(wrapper.emitted("update:range")).toEqual([["30d"]])
	})
})

describe("useOverviewTrend (#1273)", () => {
	function host(initial: OverviewTrendRange = "30d") {
		const range = ref<OverviewTrendRange>(initial)
		let state!: ReturnType<typeof useOverviewTrend>
		const wrapper = mount(
			defineComponent({
				setup() {
					state = useOverviewTrend(range)
					return () => h("div")
				}
			})
		)
		return { wrapper, range, state: () => state }
	}

	it("asks for the period and the customers in the global filter, again when either changes", async () => {
		overviewTrend.mockResolvedValue({ data: trend() })
		const { range, state } = host()
		await flushPromises()
		expect(overviewTrend.mock.calls[0]![0]).toMatchObject({ range: "30d", customerCodes: undefined })
		expect(state().days.value).toHaveLength(7)

		range.value = "7d"
		await flushPromises()
		expect(overviewTrend.mock.calls[1]![0]).toMatchObject({ range: "7d" })

		useCustomerFilterStore().setSelected(["ACME"])
		await flushPromises()
		expect(overviewTrend.mock.calls[2]![0]).toMatchObject({ range: "7d", customerCodes: ["ACME"] })
	})

	it("lets only the latest load count, and aborts the one it replaces", async () => {
		const pending: { resolve: (value: unknown) => void; signal: AbortSignal }[] = []
		overviewTrend.mockImplementation(
			({ signal }: { signal: AbortSignal }) => new Promise(resolve => pending.push({ resolve, signal }))
		)
		const { range, state } = host()
		range.value = "7d"
		await flushPromises()
		expect(pending[0]!.signal.aborted).toBe(true)

		pending[1]!.resolve({ data: trend({ range: "7d" }) })
		pending[0]!.resolve({ data: trend({ range: "30d" }) })
		await flushPromises()
		expect(state().trend.value?.range).toBe("7d")
		expect(state().loading.value).toBe(false)
	})

	it("keeps the last days when a reload fails, and reports it", async () => {
		overviewTrend.mockResolvedValueOnce({ data: trend() })
		overviewTrend.mockRejectedValueOnce(new Error("timeout"))
		const { state } = host()
		await flushPromises()
		await state().reload()
		expect(state().error.value).toContain("timeout")
		expect(state().days.value).toHaveLength(7)
	})

	it("aborts its load when the page goes away", async () => {
		let signal: AbortSignal | undefined
		overviewTrend.mockImplementation((options: { signal: AbortSignal }) => {
			signal = options.signal
			return new Promise(() => {})
		})
		const { wrapper } = host()
		wrapper.unmount()
		expect(signal?.aborted).toBe(true)
	})
})
