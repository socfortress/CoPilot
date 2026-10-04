import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import DurationCell from "../ui/DurationCell.vue"
import TargetCell from "../ui/TargetCell.vue"

describe("targetCell", () => {
	it("shows the target in full ink, in its largest exact unit", () => {
		const wrapper = mount(TargetCell, { props: { minutes: 240 } })
		const cell = wrapper.get("[data-testid=target-cell]")
		expect(cell.text()).toBe("4h")
		expect(cell.classes()).toContain("text-default")
		expect(cell.classes()).toContain("text-sm")
		expect(cell.attributes("title")).toBe("Target: 4h")
	})

	it("is a plain dash when the severity has no target", () => {
		for (const minutes of [null, undefined]) {
			const cell = mount(TargetCell, { props: { minutes } }).get("[data-testid=target-cell]")
			expect(cell.text()).toBe("—")
			expect(cell.classes()).toContain("text-tertiary")
			expect(cell.attributes("title")).toBe("No target for this severity")
		}
	})
})

describe("durationCell", () => {
	const stats = { count: 13, mean: 600, median: 420, p90: 1140 }

	it("leads with the median and puts the p90 under it", () => {
		const cell = mount(DurationCell, { props: { stats } }).get("[data-testid=duration-cell]")
		const [median, p90] = cell.findAll(":scope > span")
		expect(median.text()).toBe("7m")
		expect(median.classes()).toContain("font-medium")
		expect(p90.findAll("span").map(part => part.text())).toEqual(["p90", "19m"])
		expect(cell.classes()).toContain("items-end") // right-aligned like every figure
	})

	it("reads as a dash, with no p90, when nothing has an outcome yet", () => {
		const cell = mount(DurationCell, { props: { stats: { count: 0, mean: null, median: null, p90: null } } }).get(
			"[data-testid=duration-cell]"
		)
		expect(cell.text()).toBe("—")
		expect(cell.findAll(":scope > span")).toHaveLength(1)
	})

	it("puts the median, mean, p90 and sample size in its tooltip", async () => {
		const wrapper = mount(DurationCell, { props: { stats }, attachTo: document.body })
		await wrapper.get("[data-testid=duration-cell]").trigger("mouseenter")
		await new Promise(resolve => setTimeout(resolve, 250))
		const tooltip = document.querySelector("[data-testid=duration-cell-tooltip]")
		const pairs = [...(tooltip?.querySelectorAll("dt") ?? [])].map(term => [term.textContent?.trim(), term.nextElementSibling?.textContent?.trim()])
		expect(pairs).toEqual([
			["median", "7m"],
			["mean", "10m"],
			["p90", "19m"],
			["items", "13"]
		])
		wrapper.unmount()
	})
})
