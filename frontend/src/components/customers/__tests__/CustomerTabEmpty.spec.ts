import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { h } from "vue"
import CustomerTabEmpty from "../CustomerTabEmpty.vue"

/** A customer tab with nothing configured says what the feature is and how to start it. */
describe("customerTabEmpty", () => {
	it("shows the title, the explanation, the numbered points and the actions", () => {
		const wrapper = mount(CustomerTabEmpty, {
			props: {
				icon: "carbon:deploy",
				title: "Nothing here yet",
				description: "What the feature does.",
				points: [
					{ title: "First", description: "One." },
					{ title: "Second", description: "Two." }
				],
				note: "A note."
			},
			slots: { actions: () => h("button", { "data-testid": "start" }, "Start") }
		})
		expect(wrapper.get("[data-testid=customer-tab-empty-title]").text()).toBe("Nothing here yet")
		expect(wrapper.get("[data-testid=customer-tab-empty-eyebrow]").text()).toBe("Not set up")
		const points = wrapper.get("[data-testid=customer-tab-empty-points]").findAll("li")
		expect(points.map(point => point.text())).toEqual(["01FirstOne.", "02SecondTwo."])
		expect(wrapper.get("[data-testid=customer-tab-empty-actions]").find("[data-testid=start]").exists()).toBe(true)
		expect(wrapper.text()).toContain("A note.")
	})

	it("leaves out the points column and the actions row when there are none", () => {
		const wrapper = mount(CustomerTabEmpty, {
			props: { icon: "carbon:deploy", title: "T", description: "D", eyebrow: "Unavailable" }
		})
		expect(wrapper.find("[data-testid=customer-tab-empty-points]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=customer-tab-empty-actions]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=customer-tab-empty-eyebrow]").text()).toBe("Unavailable")
	})
})
