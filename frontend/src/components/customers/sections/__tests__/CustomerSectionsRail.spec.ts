/** The open group's rail (#1325): subgroups that fold away, lights and counts, the current item. */
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import CustomerSectionsRail from "../CustomerSectionsRail.vue"
import { groupViews, visibleSections } from "../sections"
import { statusFixture } from "./fixtures"

const groups = groupViews(visibleSections({ admin: true, automation: true, wazuhWorker: true }))
function group(id: string) {
	const found = groups.find(item => item.id === id)
	if (!found) throw new Error(`no group ${id}`)
	return found
}

const portal = group("portal")
const data = group("data")

function render(group = portal, current: string = "SLA", status = statusFixture()) {
	return mount(CustomerSectionsRail, { props: { group, current: current as never, status } })
}

describe("the section rail", () => {
	it("lists the group's sections under their subgroups, with how many are on", () => {
		const wrapper = render()
		expect(wrapper.attributes("aria-label")).toBe("Customer Portal sections")
		expect(wrapper.findAll(".rail-subgroup").map(item => item.text())).toEqual([
			"Appearance1 of 2 on",
			"Portal pages2 of 4 on",
			"AI & requests4 of 4 on",
			"Notifications"
		])
		expect(wrapper.findAll(".rail-item")).toHaveLength(11)
	})

	it("marks the current section", () => {
		const current = render().get('[data-testid="rail-item-SLA"]')
		expect(current.classes()).toContain("is-current")
		expect(current.attributes("aria-current")).toBe("page")
	})

	it("a switch has a light, filled when on and a ring when off, and its word for screen readers", () => {
		const wrapper = render()
		const sla = wrapper.get('[data-testid="rail-item-SLA"]')
		expect(sla.find(".section-led.is-on").exists()).toBe(true)
		expect(sla.get(".sr-only").text()).toBe("On")
		const activity = wrapper.get('[data-testid="rail-item-Activity"]')
		expect(activity.find(".section-led").exists()).toBe(true)
		expect(activity.find(".section-led.is-on").exists()).toBe(false)
		expect(activity.get(".sr-only").text()).toBe("Off")
	})

	it("a list has its count after the name", () => {
		const integrations = render(data, "WAF").get('[data-testid="rail-item-3rd Party Integrations"]')
		expect(integrations.get(".section-count").text()).toBe("2")
		expect(integrations.get(".sr-only").text()).toBe("2 integrations")
		expect(integrations.find(".section-led").exists()).toBe(false)
	})

	it("without a status, it lists the sections and nothing else", () => {
		const wrapper = render(portal, "SLA", null as never)
		expect(wrapper.find(".section-led").exists()).toBe(false)
		expect(wrapper.find(".rail-summary").exists()).toBe(false)
		expect(wrapper.findAll(".rail-item")).toHaveLength(11)
	})

	it("folds a subgroup away and opens it again", async () => {
		const wrapper = render()
		const appearance = wrapper.get('[data-testid="rail-subgroup-Appearance"]')
		await appearance.trigger("click")
		expect(appearance.attributes("aria-expanded")).toBe("false")
		expect(wrapper.find('[data-testid="rail-item-Portal Branding"]').exists()).toBe(false)
		await appearance.trigger("click")
		expect(wrapper.find('[data-testid="rail-item-Portal Branding"]').exists()).toBe(true)
	})

	it("opens the folded subgroup that holds the section the viewer moves to", async () => {
		const wrapper = render()
		await wrapper.get('[data-testid="rail-subgroup-AI & requests"]').trigger("click")
		expect(wrapper.find('[data-testid="rail-item-IOC Enrichment"]').exists()).toBe(false)
		await wrapper.setProps({ current: "IOC Enrichment" })
		expect(wrapper.find('[data-testid="rail-item-IOC Enrichment"]').exists()).toBe(true)
	})

	it("asks to open a section", async () => {
		const wrapper = render()
		await wrapper.get('[data-testid="rail-item-Exposure"]').trigger("click")
		expect(wrapper.emitted("select")).toEqual([["Exposure"]])
	})
})
