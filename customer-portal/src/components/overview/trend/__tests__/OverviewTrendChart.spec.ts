import type { TrendDay } from "../trend"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import OverviewTrendChart from "../OverviewTrendChart.vue"

vi.mock("vue-echarts", () => ({
	default: defineComponent({ name: "VChart", props: { option: Object }, setup: () => () => h("div") })
}))

type Option = Record<string, any>

function day(date: string, opened: number, closed: number, open: number | null): TrendDay {
	return { day: date, alerts: { opened, closed, open }, cases: { opened: 0, closed: 0, open: 0 } }
}

const DAYS: TrendDay[] = [
	day("2026-10-11", 3, 0, 7),
	day("2026-10-12", 4, 1, 10),
	day("2026-10-13", 0, 6, 4),
	day("2026-10-14", 1, 1, 4)
]

function option(days = DAYS): Option {
	const wrapper = mount(OverviewTrendChart, { props: { days, entity: "alerts" } })
	return wrapper.getComponent({ name: "VChart" }).props("option") as Option
}

beforeEach(() => setActivePinia(createPinia()))

describe("overviewTrendChart (#1273)", () => {
	it("draws what is still open above, opened up and closed down below, each band with its own scale", () => {
		const o = option()
		expect(o.grid).toHaveLength(2)
		expect(o.yAxis.map((axis: Option) => axis.name)).toEqual(["Open · at day end", "Opened ↑  Closed ↓"])
		const [open, opened, closed] = o.series
		expect(open.data).toEqual([7, 10, 4, 4])
		expect(opened.data).toEqual([3, 4, 0, 1])
		expect(closed.data).toEqual([-0, -1, -6, -1])
		// The lower axis reads counts, not signs.
		expect(o.yAxis[1].axisLabel.formatter(-6)).toBe("6")
		// One calendar: the crosshair follows both bands, and each day's point sits above its bars.
		expect(o.tooltip.axisPointer.link).toEqual([{ xAxisIndex: "all" }])
		expect(o.xAxis.map((axis: Option) => axis.boundaryGap)).toEqual([undefined, undefined])
	})

	it("marks the peak and today, and only today when today is the peak", () => {
		expect(option().series[0].markPoint.data.map((mark: Option) => mark.value)).toEqual([4, "peak 10"])
		// Above their points: beside it, today's value sat on the line.
		expect(option().series[0].markPoint.data.map((mark: Option) => mark.label.position)).toEqual(["top", "top"])
		const rising = [day("2026-10-11", 1, 0, 1), day("2026-10-12", 2, 0, 3)]
		expect(option(rising).series[0].markPoint.data.map((mark: Option) => mark.value)).toEqual([3])
	})

	it("gives the whole day in the tooltip: opened, closed, its Net and what was still open", () => {
		const html: string = option().tooltip.formatter([{ dataIndex: 2 }])
		expect(html).toContain("Opened: <b>0</b>")
		expect(html).toContain("Closed: <b>6</b>")
		expect(html).toContain("Net: <b>−6</b>")
		expect(html).toContain("Open at day end: <b>4</b>")
	})

	it("leaves the level out rather than drawing a guess when it is not known", () => {
		const unknown = DAYS.map(d => ({ ...d, alerts: { ...d.alerts, open: null } }))
		const o = option(unknown)
		expect(o.series[0].data).toEqual([null, null, null, null])
		expect(o.series[0].markPoint.data).toEqual([])
		expect(o.tooltip.formatter([{ dataIndex: 0 }])).toContain("Open at day end: <b>—</b>")
	})
})
