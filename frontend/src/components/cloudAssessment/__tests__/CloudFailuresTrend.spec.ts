/**
 * The account page's failures over time (#1328): a legend naming every severity drawn, the chart,
 * and the same numbers as a table; picking a column or a row asks for that scan.
 */
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CloudFailuresTrend from "../CloudFailuresTrend.vue"
import { trendPoints } from "../trend"
import { counts, scan } from "./fixtures"

/** What the chart stub was last given, and the click handler the component bound on it. */
const chart = vi.hoisted(() => ({
	option: null as unknown,
	onClick: null as ((event: { offsetX: number; offsetY: number }) => void) | null,
	index: 0,
	inside: true
}))

vi.mock("vue-echarts", () => ({
	default: defineComponent({
		props: { option: { type: Object, required: true } },
		setup(props, { attrs, expose }) {
			expose({ containPixel: () => chart.inside, convertFromPixel: () => [chart.index, 3] })
			return () => {
				chart.option = props.option
				chart.onClick = attrs["onZr:click"] as typeof chart.onClick
				return h("div", { "data-testid": "v-chart" })
			}
		}
	})
}))

const POINTS = trendPoints([
	scan(11, { counts: counts({ failed: 5, failed_critical: 1, failed_high: 4, new_failed: 2, resolved_failed: 3 }) }),
	scan(10, { counts: counts({ failed: 6, failed_high: 2, failed_low: 4 }), previous_scan_id: null })
])

function render(selectedId: number | null = 11) {
	return mount(CloudFailuresTrend, { props: { points: POINTS, selectedId }, attachTo: document.body })
}

beforeEach(() => {
	setActivePinia(createPinia())
	chart.option = null
	chart.onClick = null
	chart.index = 0
	chart.inside = true
})

describe("failures over time", () => {
	it("names every severity it draws, and says how many scans it covers", () => {
		const wrapper = render()
		const legend = wrapper.find("[data-testid=cloud-trend-legend]").text()
		for (const name of ["Critical", "High", "Medium", "Low", "Informational"]) expect(legend).toContain(name)
		expect(legend).not.toContain("Unknown")
		expect(wrapper.text()).toContain("2 completed scans")
		expect(wrapper.find("[data-testid=cloud-trend-chart]").exists()).toBe(true)
		expect(chart.option).not.toBeNull()
	})

	it("opens the scan of the column clicked, anywhere in its slot", async () => {
		const wrapper = render()
		chart.index = 0
		chart.onClick?.({ offsetX: 40, offsetY: 120 })
		chart.inside = false
		chart.onClick?.({ offsetX: 2, offsetY: 2 }) // outside the plot: nothing
		await flushPromises()
		expect(wrapper.emitted("select")).toEqual([[10]])
	})

	it("shows the same numbers as a table, newest first, a row opening its scan", async () => {
		const wrapper = render(10)
		await wrapper.find("[data-testid=cloud-trend-view-table]").trigger("click")
		const table = wrapper.find("[data-testid=cloud-trend-table]")
		expect(table.exists()).toBe(true)
		expect(wrapper.find("[data-testid=cloud-trend-chart]").exists()).toBe(false)
		const rows = table.findAll("tbody tr")
		expect(rows.map(row => row.attributes("data-testid"))).toEqual(["cloud-trend-row-11", "cloud-trend-row-10"])
		expect(rows[0]?.text()).toContain("2 new, 3 resolved")
		expect(rows[1]?.text()).toContain("first scan")
		expect(rows[1]?.find("button").attributes("aria-current")).toBe("true")

		await rows[0]?.find("button").trigger("click")
		expect(wrapper.emitted("select")).toEqual([[11]])
	})
})
