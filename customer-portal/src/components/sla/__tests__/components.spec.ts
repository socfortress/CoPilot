import type { SlaKpi, TargetGroup } from "../sla"
import type { SlaOpenNow as OpenNow, SlaTrendPoint } from "@/types/sla"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { rateDelta } from "../sla"
import SlaKpiCard from "../SlaKpiCard.vue"
import SlaOpenNow from "../SlaOpenNow.vue"
import SlaTargetsTable from "../SlaTargetsTable.vue"
import SlaTrendChart from "../SlaTrendChart.vue"

// The chart library draws on a canvas jsdom does not have: keep the option it is handed.
vi.mock("vue-echarts", () => ({
	default: defineComponent({
		name: "VChart",
		props: { option: { type: Object, required: true } },
		setup: () => () => h("div", { "data-testid": "chart-stub" })
	})
}))

/** RouterLink without a router: render the target as data so the test can read it. */
const RouterLinkStub = defineComponent({
	props: { to: { type: Object, required: true } },
	setup(props, { slots }) {
		return () => h("a", { "data-to": JSON.stringify(props.to) }, slots.default?.())
	}
})

beforeEach(() => setActivePinia(createPinia()))

function kpi(overrides: Partial<SlaKpi> = {}): SlaKpi {
	return {
		key: "alert-acknowledge",
		entity: "alert",
		clock: "acknowledge",
		title: "Alert response",
		caption: "answered within target",
		rate: 83.3,
		met: 5,
		decided: 6,
		delta: rateDelta(83.3, 90),
		medianLabel: "median response",
		median: "10m",
		...overrides
	}
}

describe("slaKpiCard (#1187)", () => {
	it("shows the rate, the change against the previous period, the count and the median", () => {
		const wrapper = mount(SlaKpiCard, { props: { kpi: kpi() } })
		expect(wrapper.get("[data-testid=sla-kpi-rate]").text()).toBe("83.3%")
		expect(wrapper.get("[data-testid=sla-kpi-delta]").text()).toBe("-6.7")
		expect(wrapper.get("[data-testid=sla-kpi-delta]").classes()).toContain("text-error")
		expect(wrapper.get("[data-testid=sla-kpi-count]").text()).toBe("5 of 6 on target")
		expect(wrapper.get("[data-testid=sla-kpi-median]").text()).toBe("10m")
	})

	it("says an improvement in points, with a plus", () => {
		const wrapper = mount(SlaKpiCard, { props: { kpi: kpi({ rate: 100, delta: rateDelta(100, 90) }) } })
		expect(wrapper.get("[data-testid=sla-kpi-delta]").text()).toBe("+10.0")
		expect(wrapper.get("[data-testid=sla-kpi-delta]").classes()).toContain("text-success")
	})

	it("shows no outcome as a dash, with no delta and no count, never as 0%", () => {
		const wrapper = mount(SlaKpiCard, {
			props: { kpi: kpi({ rate: null, met: 0, decided: 0, delta: rateDelta(null, 90), median: "—" }) }
		})
		expect(wrapper.get("[data-testid=sla-kpi-rate]").text()).toBe("—")
		expect(wrapper.find("[data-testid=sla-kpi-delta]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=sla-kpi-count]").text()).toBe("no outcome yet")
		expect(wrapper.get("[data-testid=sla-kpi-rate]").classes()).toContain("text-tertiary")
	})
})

describe("slaOpenNow (#1187)", () => {
	const openNow: OpenNow = { alerts: 5, cases: 2, breached: 0, at_risk: 1, waiting_on_you: 3 }

	function mountOpenNow(value: OpenNow = openNow) {
		return mount(SlaOpenNow, { props: { openNow: value }, global: { stubs: { RouterLink: RouterLinkStub } } })
	}

	it("counts what is open now, whatever the period", () => {
		const wrapper = mountOpenNow()
		const value = (key: string) => wrapper.get(`[data-testid=sla-open-${key}] [data-testid=sla-open-value]`).text()
		expect([value("alerts"), value("cases"), value("at-risk"), value("breached"), value("waiting")]).toEqual([
			"5",
			"2",
			"1",
			"0",
			"3"
		])
		// A zero is never alarming: no warning colour on it.
		expect(wrapper.get("[data-testid=sla-open-breached] [data-testid=sla-open-value]").classes()).not.toContain(
			"text-error"
		)
	})

	it("links what waits on the customer to both lists, filtered on that status", () => {
		const wrapper = mountOpenNow()
		const to = (link: string) =>
			JSON.parse(wrapper.get(`[data-testid=sla-open-waiting-${link}]`).attributes("data-to") as string)
		expect(to("alerts")).toEqual({ name: "AlertsList", query: { status: "PENDING_CUSTOMER" } })
		expect(to("cases")).toEqual({ name: "CasesList", query: { status: "PENDING_CUSTOMER" } })
	})

	it("links the open alerts and cases to their whole lists: open is every status but closed", () => {
		const wrapper = mountOpenNow()
		const to = (key: string) =>
			JSON.parse(wrapper.get(`[data-testid=sla-open-${key}-view-all]`).attributes("data-to") as string)
		expect(to("alerts")).toEqual({ name: "AlertsList" })
		expect(to("cases")).toEqual({ name: "CasesList" })
		expect(wrapper.get("[data-testid=sla-open-alerts-view-all]").text()).toContain("View all")
		// Nothing open, nothing to view.
		const empty = mountOpenNow({ ...openNow, alerts: 0, cases: 0 })
		expect(empty.find("[data-testid=sla-open-alerts-view-all]").exists()).toBe(false)
		expect(empty.find("[data-testid=sla-open-cases-view-all]").exists()).toBe(false)
	})

	it("offers no link when nothing waits on the customer", () => {
		const wrapper = mountOpenNow({ ...openNow, waiting_on_you: 0 })
		expect(wrapper.find("[data-testid=sla-open-waiting-alerts]").exists()).toBe(false)
	})
})

describe("slaTargetsTable (#1187)", () => {
	const groups: TargetGroup[] = [
		{
			entity: "alert",
			title: "Alerts",
			rows: [
				{
					entity: "alert",
					severity: "Critical",
					acknowledge_minutes: 15,
					resolve_minutes: 240,
					business_hours: true,
					opened: 4,
					acknowledge_rate: 100,
					resolve_rate: 75,
					time_to_resolve: 3600
				},
				{
					entity: "alert",
					severity: "Low",
					acknowledge_minutes: 480,
					resolve_minutes: null,
					business_hours: false,
					opened: 0,
					acknowledge_rate: null,
					resolve_rate: null,
					time_to_resolve: null
				}
			]
		}
	]

	it("states each promise in its unit, marks business hours and says how it was kept", () => {
		const wrapper = mount(SlaTargetsTable, { props: { groups } })
		const critical = wrapper.get("[data-testid=sla-target-alert-critical]")
		expect(critical.text()).toContain("15 min")
		expect(critical.text()).toContain("4 h")
		expect(critical.find("[data-testid=sla-business-hours]").exists()).toBe(true)
		expect(critical.text()).toContain("75%")
	})

	it("shows a dash for a severity with nothing in the period, and no target as such", () => {
		const low = mount(SlaTargetsTable, { props: { groups } }).get("[data-testid=sla-target-alert-low]")
		expect(low.text()).toContain("No target")
		expect(low.text()).toContain("—")
		expect(low.find("[data-testid=sla-business-hours]").exists()).toBe(false)
	})
})

describe("slaTrendChart (#1187)", () => {
	const points: SlaTrendPoint[] = [
		{ start: "2026-09-01T00:00:00", opened: 4, resolved: 3, rate: 75 },
		{ start: "2026-09-02T00:00:00", opened: 0, resolved: 0, rate: null },
		{ start: "2026-09-03T00:00:00", opened: 2, resolved: 2, rate: 100 }
	]

	function option(value: SlaTrendPoint[]) {
		const wrapper = mount(SlaTrendChart, { props: { points: value, bucket: "day" } })
		return {
			wrapper,

			option: wrapper.findComponent({ name: "VChart" }).props("option") as any
		}
	}

	it("plots one measure on one axis: the share on target, 0 to 100%", () => {
		const { option: chart, wrapper } = option(points)
		expect(Array.isArray(chart.yAxis)).toBe(false)
		expect(chart.yAxis).toMatchObject({ min: 0, max: 100, axisLabel: { formatter: "{value}%" } })
		expect(chart.series).toHaveLength(1)
		expect(chart.series[0].data).toEqual([75, null, 100])
		expect(chart.series[0].connectNulls).toBe(false)
		expect(wrapper.get("[data-testid=sla-trend-chart]").attributes("aria-label")).toBe(
			"Resolution on target per period, from 75% to 100%"
		)
	})

	it("carries the volumes in the tooltip rather than on a second axis", () => {
		const { option: chart } = option(points)
		const html = chart.tooltip.formatter([{ dataIndex: 0, marker: "" }]) as string
		expect(html).toContain("75%")
		expect(html).toContain("Opened 4 · resolved 3")
	})

	it("says so when no bucket has an outcome, instead of drawing a flat line", () => {
		const { option: chart } = option([{ start: "2026-09-01T00:00:00", opened: 1, resolved: 0, rate: null }])
		expect(chart.series).toBeUndefined()
		expect(chart.title.text).toBe("No resolution outcome yet")
	})
})
