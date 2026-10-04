import type { Component } from "vue"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { defineComponent, h, ref } from "vue"
import SegmentedToggle from "../SegmentedToggle.vue"

function toggle(initial = "alert") {
	const value = ref(initial)
	const Host = defineComponent({
		setup: () => () =>
			// A generic SFC: h() cannot infer T from the props object, so it is passed untyped.
			h(SegmentedToggle as unknown as Component, {
				modelValue: value.value,
				"onUpdate:modelValue": (next: string) => {
					value.value = next
				},
				options: [
					{ value: "alert", label: "Alerts" },
					{ value: "case", label: "Cases" }
				],
				label: "Show",
				testId: "volume-entity"
			})
	})
	return { wrapper: mount(Host, { attachTo: document.body }), value }
}

describe("segmentedToggle", () => {
	it("is one radio group with the chosen segment checked and alone in the tab order", () => {
		const { wrapper } = toggle()
		const group = wrapper.get("[data-testid=volume-entity]")
		expect(group.attributes("role")).toBe("radiogroup")
		expect(group.attributes("aria-label")).toBe("Show")
		const alerts = wrapper.get("[data-testid=volume-entity-alert]")
		const cases = wrapper.get("[data-testid=volume-entity-case]")
		expect([alerts.attributes("aria-checked"), cases.attributes("aria-checked")]).toEqual(["true", "false"])
		expect([alerts.attributes("tabindex"), cases.attributes("tabindex")]).toEqual(["0", "-1"])
		expect(group.classes()).toContain("h-5.5") // never taller than a panel header's tiny buttons
		wrapper.unmount()
	})

	it("picks a segment on click", async () => {
		const { wrapper, value } = toggle()
		await wrapper.get("[data-testid=volume-entity-case]").trigger("click")
		expect(value.value).toBe("case")
		wrapper.unmount()
	})

	it("moves with the arrow keys, wrapping around, and keeps focus on the choice", async () => {
		const { wrapper, value } = toggle()
		const group = wrapper.get("[data-testid=volume-entity]")
		await group.trigger("keydown", { key: "ArrowRight" })
		expect(value.value).toBe("case")
		expect(document.activeElement?.getAttribute("data-testid")).toBe("volume-entity-case")
		await group.trigger("keydown", { key: "ArrowRight" })
		expect(value.value).toBe("alert")
		await group.trigger("keydown", { key: "ArrowLeft" })
		expect(value.value).toBe("case")
		await group.trigger("keydown", { key: "Enter" })
		expect(value.value).toBe("case")
		wrapper.unmount()
	})
})
