import type { TrendPoint } from "@/types/soc-management"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { useThemeStore } from "@/stores/theme"
import { ThemeNameEnum } from "@/types/theme"
import { useSocChartColors } from "../charts/chart-colors"
import ComplianceTrendChart from "../charts/ComplianceTrendChart.vue"
import VolumeTrendChart from "../charts/VolumeTrendChart.vue"

interface Series {
	type: string
	name: string
	data: (number | null)[]
	connectNulls?: boolean
	lineStyle: { width: number; color: string }
	areaStyle?: { opacity: number }
	markLine?: { data: { yAxis: number }[]; label: { formatter: string } }
}
interface Option {
	xAxis: { type: string; data: string[] }
	yAxis: { type: string; min?: number; max?: number } | unknown[]
	series: Series[]
}

/** VChart replaced by a stub that keeps the option it was given, so the spec reads it. */
const rendered: Option[] = []
vi.mock("vue-echarts", () => ({
	default: defineComponent({
		props: { option: { type: Object, required: true } },
		setup(props) {
			return () => {
				rendered.push(props.option as Option)
				return h("div", { "data-testid": "v-chart" })
			}
		}
	})
}))

function point(day: number, over: Partial<TrendPoint> = {}): TrendPoint {
	return {
		start: `2026-09-${String(day).padStart(2, "0")}T00:00:00`,
		alerts_opened: 10,
		alerts_resolved: 8,
		cases_opened: 1,
		cases_resolved: 0,
		sla_rate: 90,
		alert_ttr_median: 3600,
		...over
	}
}

const lastOption = () => rendered.at(-1) as Option

beforeEach(() => {
	setActivePinia(createPinia())
	rendered.length = 0
})

describe("chart colours", () => {
	it("steps the brand amber and its blue per mode, separately from status colours", () => {
		const theme = useThemeStore()
		theme.setTheme(ThemeNameEnum.Light)
		const colors = useSocChartColors()
		expect([colors.mode.value, colors.primary.value, colors.secondary.value]).toEqual(["light", "#A87400", "#2A78D6"])
		theme.setTheme(ThemeNameEnum.Dark)
		expect([colors.mode.value, colors.primary.value, colors.secondary.value]).toEqual(["dark", "#C98500", "#3987E5"])
	})
})

describe("complianceTrendChart", () => {
	it("draws one series on one 0–100% axis, with the objective as a reference line", () => {
		mount(ComplianceTrendChart, { props: { points: [point(1), point(2, { sla_rate: null }), point(3, { sla_rate: 80 })], bucket: "day", objective: 95 } })
		const option = lastOption()
		expect(option.series).toHaveLength(1)
		const [series] = option.series
		expect(series.data).toEqual([90, null, 80])
		expect(series.connectNulls).toBe(false) // a bucket with no outcome is a gap, never 0%
		expect(series.lineStyle.width).toBe(2)
		expect(series.markLine?.data).toEqual([{ yAxis: 95 }])
		expect(series.markLine?.label.formatter).toBe("95%")
		expect(Array.isArray(option.yAxis)).toBe(false)
		expect(option.yAxis).toMatchObject({ type: "value", min: 0, max: 100 })
		expect(option.xAxis.data).toHaveLength(3)
	})

	it("says there is nothing yet instead of drawing an empty chart", () => {
		const wrapper = mount(ComplianceTrendChart, { props: { points: [point(1, { sla_rate: null })], bucket: "day" } })
		expect(wrapper.find("[data-testid=v-chart]").exists()).toBe(false)
		expect(wrapper.text()).toContain("No SLA outcome in this period yet")
	})
})

describe("volumeTrendChart", () => {
	it("draws opened and resolved on one axis, washing only the lead series", () => {
		const wrapper = mount(VolumeTrendChart, { props: { points: [point(1), point(2, { alerts_opened: 5 })], bucket: "day" } })
		const option = lastOption()
		expect(option.series.map(s => [s.name, s.data])).toEqual([
			["Opened", [10, 5]],
			["Resolved", [8, 8]]
		])
		expect(option.series[0].areaStyle?.opacity).toBe(0.1)
		expect(option.series[1].areaStyle).toBeUndefined()
		expect(Array.isArray(option.yAxis)).toBe(false) // one axis: same unit
		expect(wrapper.text()).toContain("Opened 15")
		expect(wrapper.text()).toContain("Resolved 16")
	})

	it("switches to cases, and is empty when nothing moved", () => {
		mount(VolumeTrendChart, { props: { points: [point(1)], bucket: "day", entity: "case" } })
		expect(lastOption().series.map(s => s.data)).toEqual([[1], [0]])
		const empty = mount(VolumeTrendChart, {
			props: { points: [point(1, { cases_opened: 0, cases_resolved: 0 })], bucket: "day", entity: "case" }
		})
		expect(empty.text()).toContain("No cases in this period")
	})
})
