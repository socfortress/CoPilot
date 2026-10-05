import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import WorkflowStatusStrip from "../WorkflowStatusStrip.vue"

const counts = { total: 6, open: 3, in_progress: 2, pending_customer: 0, closed: 1 }

function strip(value = counts) {
	return mount(WorkflowStatusStrip, { props: { counts: value, entity: "Alerts", icon: "carbon:warning-alt" } })
}

describe("workflowStatusStrip", () => {
	it("leads with the total and splits it by status, with each status's share", () => {
		const wrapper = strip()
		expect(wrapper.get("section").attributes("aria-label")).toBe("Alerts by status")
		expect(wrapper.get("[data-testid=stat-total]").text()).toContain("Total alerts")
		expect(wrapper.get("[data-testid=stat-total] [data-testid=stat-value]").text()).toBe("6")
		const value = (key: string) => wrapper.get(`[data-testid=stat-${key}] [data-testid=stat-value]`).text()
		const share = (key: string) => wrapper.get(`[data-testid=stat-${key}] [data-testid=stat-share]`).text()
		expect(["open", "in_progress", "pending_customer", "closed"].map(value)).toEqual(["3", "2", "0", "1"])
		expect(["open", "in_progress", "pending_customer", "closed"].map(share)).toEqual(["50%", "33%", "0%", "17%"])
		// The bar under the total carries the same split, named for screen readers.
		const bar = wrapper.findAll("[data-testid=stat-total] [role=img]").at(-1) // the first one is the label's icon
		expect(bar?.attributes("aria-label")).toBe(
			"3 open, 2 in progress, 0 waiting on you, 1 closed"
		)
	})

	it("uses the shared status palette: open is the lists' blue, not an alarm", () => {
		const wrapper = strip()
		expect(wrapper.get("[data-testid=stat-open] .rounded-full").classes()).toContain("bg-info")
		expect(wrapper.get("[data-testid=stat-closed] .rounded-full").classes()).toContain("bg-success")
	})

	it("lifts 'waiting on you' only while something waits on the customer", () => {
		expect(strip().get("[data-testid=stat-pending_customer]").classes()).not.toContain("is-waiting")
		const waiting = strip({ ...counts, pending_customer: 2 })
		expect(waiting.get("[data-testid=stat-pending_customer]").classes()).toContain("is-waiting")
		expect(waiting.get("[data-testid=stat-pending_customer] [data-testid=stat-value]").classes()).toContain(
			"text-primary"
		)
	})

	it("shows no share when there is nothing to share out", () => {
		const wrapper = strip({ total: 0, open: 0, in_progress: 0, pending_customer: 0, closed: 0 })
		expect(wrapper.get("[data-testid=stat-open] [data-testid=stat-share]").text()).toBe("")
	})
})
