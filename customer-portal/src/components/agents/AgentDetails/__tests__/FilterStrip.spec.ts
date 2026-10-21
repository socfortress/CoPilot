import type { FilterStripOption } from "../FilterStrip.vue"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import FilterStrip from "../FilterStrip.vue"

function options(values: string[]): FilterStripOption[] {
	return values.map((value, index) => ({ value, label: value, count: index, dot: "bg-muted" }))
}

function render(values: string[]) {
	return mount(FilterStrip, {
		props: { options: options(values), label: "Filter", testid: "strip", modelValue: values[0] }
	})
}

/** The strip on a narrow column (#1289): five cells don't fit side by side there. */
describe("filterStrip", () => {
	it("gives the first of five cells a row of its own below the large container size", () => {
		const wrapper = render(["All", "Critical", "High", "Medium", "Low"])
		const strip = wrapper.get("[role=group]")
		expect(strip.attributes("data-split")).toBe("true")
		expect(strip.classes()).toContain("grid-cols-[repeat(var(--rest),minmax(0,1fr))]")
		expect(strip.attributes("style")).toContain("--rest: 4")
		const [first, second, third] = wrapper.findAll("button")
		expect(first!.classes()).toEqual(expect.arrayContaining(["col-span-full", "@lg:col-span-1", "flex-row!"]))
		// The first cell of the second row has no left border there; the others keep theirs.
		expect(second!.classes()).not.toContain("border-l")
		expect(third!.classes()).toContain("border-l")
	})

	it("keeps four cells on one row at every size", () => {
		const wrapper = render(["all", "failed", "passed", "na"])
		const strip = wrapper.get("[role=group]")
		expect(strip.attributes("data-split")).toBeUndefined()
		expect(strip.classes()).toContain("grid-cols-[repeat(var(--all),minmax(0,1fr))]")
		expect(wrapper.findAll("button")[0]!.classes()).not.toContain("col-span-full")
	})

	it("is still the filter: a click selects the cell", async () => {
		const wrapper = render(["All", "Critical", "High", "Medium", "Low"])
		await wrapper.get("[data-testid=strip-High]").trigger("click")
		expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["High"])
	})
})
