/**
 * The bar above a customer's sections (#1325): a group's menu previews what each section holds
 * before it is opened, the pinned sections, and the search over every section.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NAutoComplete } from "naive-ui"
import { afterEach, beforeAll, describe, expect, it } from "vitest"
import { nextTick } from "vue"
import CustomerSectionsBar from "../CustomerSectionsBar.vue"
import { groupViews, visibleSections } from "../sections"
import { statusFixture } from "./fixtures"

const sections = visibleSections({ admin: true, automation: true, wazuhWorker: false })

function render(props: Partial<InstanceType<typeof CustomerSectionsBar>["$props"]> = {}) {
	return mount(CustomerSectionsBar, {
		props: {
			groups: groupViews(sections),
			sections,
			current: "Info",
			status: statusFixture(),
			pinned: [],
			...props
		},
		attachTo: document.body
	})
}

function inBody(selector: string): HTMLElement | null {
	return document.body.querySelector<HTMLElement>(selector)
}

async function settle() {
	await flushPromises()
	await new Promise(resolve => setTimeout(resolve, 0))
	await flushPromises()
}

enableAutoUnmount(afterEach)

// The search's menu asks for the viewer's motion preference and scrolls its list; jsdom does neither.
beforeAll(() => {
	Element.prototype.scrollTo ??= () => {}
	window.matchMedia ??= (query: string) =>
		({
			matches: false,
			media: query,
			onchange: null,
			addListener: () => {},
			removeListener: () => {},
			addEventListener: () => {},
			removeEventListener: () => {},
			dispatchEvent: () => false
		}) as MediaQueryList
})

describe("the group menus", () => {
	it("marks the open section's group", () => {
		const wrapper = render({ current: "IOC Enrichment" })
		const portal = wrapper.get('[data-testid="section-group-portal"]')
		expect(portal.classes()).toContain("is-current")
		expect(portal.attributes("aria-current")).toBe("true")
		expect(wrapper.get('[data-testid="section-group-overview"]').attributes("aria-current")).toBeUndefined()
	})

	it("opens from the keyboard with every section's state, worded, and moves focus into it", async () => {
		const wrapper = render()
		await wrapper.get('[data-testid="section-group-portal"]').trigger("keydown", { key: "ArrowDown" })
		await settle()
		const menu = inBody('[data-testid="section-menu-portal"]')
		expect(menu).not.toBeNull()
		expect(menu?.textContent).toContain("7 of 10 on")
		const languages = inBody('[data-testid="section-menu-item-Portal Languages"]')
		expect(languages?.textContent).toContain("Languages")
		expect(languages?.textContent).toContain("English only")
		expect(inBody('[data-testid="section-menu-item-AI Report"]')?.textContent).toContain("On · chat on")
		expect(inBody('[data-testid="section-menu-item-Activity"]')?.textContent).toContain("Off")
		expect(document.activeElement).toBe(inBody('[data-testid="section-menu-item-Portal Branding"]'))
	})

	it("arrow keys move through the menu; Escape closes it and gives focus back", async () => {
		const wrapper = render()
		await wrapper.get('[data-testid="section-group-data"]').trigger("keydown", { key: "ArrowDown" })
		await settle()
		const menu = inBody('[data-testid="section-menu-data"]') as HTMLElement
		menu.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }))
		expect(document.activeElement).toBe(inBody('[data-testid="section-menu-item-Network Connectors"]'))
		menu.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))
		await settle()
		expect(document.activeElement).toBe(wrapper.get('[data-testid="section-group-data"]').element)
	})

	it("a section of the menu opens it; 'Open group' opens the group", async () => {
		const wrapper = render()
		await wrapper.get('[data-testid="section-group-portal"]').trigger("keydown", { key: "ArrowDown" })
		await settle()
		inBody('[data-testid="section-menu-item-SLA"]')?.click()
		expect(wrapper.emitted("select")).toEqual([["SLA"]])
		await wrapper.get('[data-testid="section-group-automation"]').trigger("keydown", { key: "ArrowDown" })
		await settle()
		inBody('[data-testid="section-menu-automation"] [data-testid="section-menu-open-group"]')?.click()
		expect(wrapper.emitted("openGroup")).toEqual([["automation"]])
	})

	it("a group of one section is a plain button, and a click on any group opens it", async () => {
		const wrapper = render()
		const reports = wrapper.get('[data-testid="section-group-reports"]')
		expect(reports.attributes("aria-haspopup")).toBeUndefined()
		await reports.trigger("click")
		await wrapper.get('[data-testid="section-group-agents"]').trigger("click")
		expect(wrapper.emitted("openGroup")).toEqual([["reports"], ["agents"]])
	})
})

describe("the pinned sections", () => {
	it("lists them with their group, opens one and unpins one", async () => {
		const wrapper = render({ pinned: ["Event Sources", "Security"] })
		expect(wrapper.get('[data-testid="sections-pinned"]').text()).toContain("2")
		await wrapper.get('[data-testid="sections-pinned"]').trigger("click")
		await settle()
		expect(inBody('[data-testid="sections-pinned-item-Event Sources"]')?.textContent).toContain("Data sources")
		inBody('[data-testid="sections-unpin-Security"]')?.click()
		expect(wrapper.emitted("togglePin")).toEqual([["Security"]])
		inBody('[data-testid="sections-pinned-item-Event Sources"]')?.click()
		expect(wrapper.emitted("select")).toEqual([["Event Sources"]])
	})

	it("is not there while nothing is pinned, nor for a pin the viewer can no longer open", async () => {
		const empty = render()
		expect(empty.find('[data-testid="sections-pinned"]').exists()).toBe(false)
		expect(empty.find(".bar-divider").exists()).toBe(false)

		const analyst = visibleSections({ admin: false, automation: false, wazuhWorker: false })
		const wrapper = render({ sections: analyst, groups: groupViews(analyst), pinned: ["Security"] })
		expect(wrapper.find('[data-testid="sections-pinned"]').exists()).toBe(false)
	})

	it("goes away, closed, when the last pin is taken off", async () => {
		const wrapper = render({ pinned: ["SLA"] })
		await wrapper.get('[data-testid="sections-pinned"]').trigger("click")
		await settle()
		expect(inBody('[data-testid="sections-pinned-menu"]')).not.toBeNull()
		await wrapper.setProps({ pinned: [] })
		await settle()
		expect(wrapper.find('[data-testid="sections-pinned"]').exists()).toBe(false)
		await wrapper.setProps({ pinned: ["WAF"] })
		await settle()
		expect(wrapper.find('[data-testid="sections-pinned"]').exists()).toBe(true)
		expect(inBody('[data-testid="sections-pinned-menu"]')).toBeNull()
	})
})

describe("the search", () => {
	it("'/' focuses it unless the viewer is typing", async () => {
		const wrapper = render()
		const input = wrapper.get('[data-testid="sections-search"] input').element as HTMLInputElement
		document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "/", bubbles: true }))
		await nextTick()
		expect(document.activeElement).toBe(input)
		input.blur()
		const other = document.createElement("textarea")
		document.body.appendChild(other)
		other.focus()
		other.dispatchEvent(new KeyboardEvent("keydown", { key: "/", bubbles: true }))
		await nextTick()
		expect(document.activeElement).toBe(other)
		other.remove()
	})

	it("finds sections and opens the one chosen, then empties", async () => {
		const wrapper = render()
		const input = wrapper.get('[data-testid="sections-search"] input')
		await input.setValue("ioc")
		await settle()
		const search = wrapper.findComponent(NAutoComplete)
		expect(search.props("options")).toEqual([{ label: "IOC Enrichment", value: "IOC Enrichment" }])
		search.vm.$emit("select", "IOC Enrichment")
		// The section opens once the search has closed its menu.
		expect(wrapper.emitted("select")).toBeUndefined()
		await settle()
		expect(wrapper.emitted("select")).toEqual([["IOC Enrichment"]])
		expect((input.element as HTMLInputElement).value).toBe("")
	})
})
