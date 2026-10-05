import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { agentStatusCells, agentStatusSplit } from "@/components/agents/agentStats"
import { workflowSegments } from "@/components/overview/posture/postureCells"
import StatusStrip from "../StatusStrip.vue"

const counts = { total: 6, open: 3, in_progress: 2, pending_customer: 0, closed: 1 }

function workflow(value = counts) {
	return mount(StatusStrip, {
		props: {
			total: value.total,
			entity: "Alerts",
			icon: "carbon:warning-alt",
			cells: workflowSegments(value),
			lift: "pending_customer"
		}
	})
}

function bar(wrapper: ReturnType<typeof workflow>) {
  return wrapper.findAll("[data-testid=stat-total] [role=img]").at(-1)
} // the first one is the label's icon

describe("statusStrip", () => {
	it("leads with the total and splits it by status, with each status's share", () => {
		const wrapper = workflow()
		expect(wrapper.get("section").attributes("aria-label")).toBe("Alerts by status")
		expect(wrapper.get("section").classes()).toContain("@3xl:grid-cols-5")
		expect(wrapper.get("[data-testid=stat-total]").text()).toContain("Total alerts")
		expect(wrapper.get("[data-testid=stat-total] [data-testid=stat-value]").text()).toBe("6")
		const value = (key: string) => wrapper.get(`[data-testid=stat-${key}] [data-testid=stat-value]`).text()
		const share = (key: string) => wrapper.get(`[data-testid=stat-${key}] [data-testid=stat-share]`).text()
		expect(["open", "in_progress", "pending_customer", "closed"].map(value)).toEqual(["3", "2", "0", "1"])
		expect(["open", "in_progress", "pending_customer", "closed"].map(share)).toEqual(["50%", "33%", "0%", "17%"])
		expect(bar(wrapper)?.attributes("aria-label")).toBe("3 open, 2 in progress, 0 waiting on you, 1 closed")
	})

	it("uses the shared status palette: open is the lists' blue, not an alarm", () => {
		const wrapper = workflow()
		expect(wrapper.get("[data-testid=stat-open] .rounded-full").classes()).toContain("bg-info")
		expect(wrapper.get("[data-testid=stat-closed] .rounded-full").classes()).toContain("bg-success")
	})

	it("lifts the named cell only while it is not zero", () => {
		expect(workflow().get("[data-testid=stat-pending_customer]").classes()).not.toContain("is-lifted")
		const waiting = workflow({ ...counts, pending_customer: 2 })
		expect(waiting.get("[data-testid=stat-pending_customer]").classes()).toContain("is-lifted")
		expect(waiting.get("[data-testid=stat-pending_customer] [data-testid=stat-value]").classes()).toContain(
			"text-primary"
		)
	})

	it("shows no share when there is nothing to share out", () => {
		const wrapper = workflow({ total: 0, open: 0, in_progress: 0, pending_customer: 0, closed: 0 })
		expect(wrapper.get("[data-testid=stat-open] [data-testid=stat-share]").text()).toBe("")
	})

	it("agents: active and offline split the bar; critical is a flag across it, with an icon", () => {
		const stats = { total: 5, active: 2, offline: 2, critical: 1 }
		const wrapper = mount(StatusStrip, {
			props: {
				total: stats.total,
				entity: "Agents",
				icon: "carbon:laptop",
				cells: agentStatusCells(stats),
				split: agentStatusSplit(stats)
			}
		})
		expect(wrapper.get("section").classes()).toContain("@3xl:grid-cols-4")
		const value = (key: string) => wrapper.get(`[data-testid=stat-${key}] [data-testid=stat-value]`).text()
		expect(["active", "offline", "critical"].map(value)).toEqual(["2", "2", "1"])
		// Critical carries an icon, not a dot, and is no share of the bar.
		expect(wrapper.get("[data-testid=stat-critical]").find(".rounded-full").exists()).toBe(false)
		expect(wrapper.get("[data-testid=stat-active]").find(".rounded-full").exists()).toBe(true)
		// One agent is neither active nor offline (pending): the bar still adds up to the total.
		expect(bar(wrapper)?.attributes("aria-label")).toBe("2 active, 2 offline, 1 other")
		expect(wrapper.find("[data-testid=stat-other]").exists()).toBe(false)
	})

	it("gives an odd last cell the whole row while the strip is two to a row", () => {
		const agents = mount(StatusStrip, {
			props: {
				total: 3,
				entity: "Agents",
				icon: "carbon:laptop",
				cells: agentStatusCells({ total: 3, active: 2, offline: 1, critical: 1 })
			}
		})
		expect(agents.get("[data-testid=stat-critical]").classes()).toContain("col-span-2")
		expect(agents.get("[data-testid=stat-offline]").classes()).not.toContain("col-span-2")
		// Four statuses fill two rows: none spans.
		expect(workflow().get("[data-testid=stat-closed]").classes()).not.toContain("col-span-2")
	})

	it("agents: no 'other' share when active and offline make up the total", () => {
		expect(agentStatusSplit({ total: 3, active: 2, offline: 1, critical: 1 }).map(s => s.key)).toEqual([
			"active",
			"offline"
		])
	})
})
