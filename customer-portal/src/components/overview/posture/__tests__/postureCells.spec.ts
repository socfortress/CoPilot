import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { describe, expect, it } from "vitest"
import Sparkline from "../../shared/Sparkline.vue"
import PostureCell from "../PostureCell.vue"
import { buildPostureCells } from "../postureCells"

const counts = { total: 10, open: 3, in_progress: 2, pending_customer: 1, closed: 4 }
const agents = { total: 1, online: 1, offline: 0, critical: 0 }

describe("posture cells", () => {
	it("break a total down into every status, waiting on the customer included (#1187)", () => {
		const counts = { total: 10, open: 3, in_progress: 2, pending_customer: 1, closed: 4 }
		const [alerts] = buildPostureCells({
			alerts: counts,
			cases: { ...counts },
			agents: { total: 1, online: 1, offline: 0, critical: 0 }
		})
		const segments = alerts!.segments
		expect(segments.map(segment => segment.label)).toEqual(["open", "in progress", "waiting on you", "closed"])
		// The bar and its legend add up to the footnote's total.
		expect(segments.reduce((sum, segment) => sum + segment.value, 0)).toBe(counts.total)
		expect(alerts!.footnote).toBe("10 total")
	})

	it("draw what was opened per day on the alerts and cases cells, not on the agents (#1273)", () => {
		const trend = { alerts: [0, 2, 1], cases: [1, 0, 0], range: "7d" }
		const [alerts, cases, agentsCell] = buildPostureCells({ alerts: counts, cases: counts, agents, trend })
		expect(alerts!.spark).toEqual({
			values: [0, 2, 1],
			caption: "opened · 7d",
			label: "3 alerts opened over the last 3 days"
		})
		expect(cases!.spark?.label).toBe("1 case opened over the last 3 days")
		expect(agentsCell!.spark).toBeUndefined()
	})

	it("draw no sparkline before the trend arrives, or for an entity whose trend failed (#1273)", () => {
		expect(buildPostureCells({ alerts: counts, cases: counts, agents })[0]!.spark).toBeUndefined()
		const [alerts, cases] = buildPostureCells({
			alerts: counts,
			cases: counts,
			agents,
			trend: { alerts: [1, 2], cases: [1, 2], range: "7d", alertsFailed: true }
		})
		expect(alerts!.spark).toBeUndefined()
		expect(cases!.spark).toBeDefined()
	})

	it("render the sparkline in the cell (#1273)", () => {
		setActivePinia(createPinia())
		const [cell] = buildPostureCells({ alerts: counts, cases: counts, agents, trend: { alerts: [0, 4, 2], cases: [], range: "30d" } })
		const wrapper = mount(PostureCell, { props: { cell: cell! }, global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } } })
		const spark = wrapper.get("[data-testid=posture-spark]")
		expect(spark.text()).toContain("opened · 30d")
		expect(spark.get("svg").attributes("aria-label")).toBe("6 alerts opened over the last 3 days")
	})
})

describe("sparkline (#1273)", () => {
	it("scales the busiest day to the top and a quiet one to the bottom", () => {
		const points = mount(Sparkline, { props: { values: [0, 4, 2], label: "x" } }).get("polyline").attributes("points")
		expect(points).toBe("0.00,27.00 50.00,1.00 100.00,14.00")
	})

	it("draws a dashed baseline when nothing happened, rather than a line at zero", () => {
		const wrapper = mount(Sparkline, { props: { values: [0, 0, 0], label: "x" } })
		expect(wrapper.find("polyline").exists()).toBe(false)
		expect(wrapper.get("line").attributes("stroke-dasharray")).toBe("2 4")
	})
})
