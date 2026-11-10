/**
 * The Knowledge bar sits under the app's toolbar, with its backdrop, only when it shares the
 * page's scroller with that toolbar; in a modal it sticks to the top and draws none.
 */
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"
import CustomerKnowledgeNav from "../CustomerKnowledgeNav.vue"

const props = { links: [{ id: "network_zone", label: "Network zones", count: 2 }], active: "network_zone" }

let page: HTMLElement | null = null

afterEach(() => {
	page?.remove()
	page = null
})

function pageWithToolbar() {
	page = document.createElement("div")
	page.className = "n-scrollbar-container"
	page.innerHTML = '<header class="toolbar"></header><div class="host"></div>'
	document.body.appendChild(page)
	return page.querySelector(".host") as HTMLElement
}

describe("the bar's place", () => {
	it("is under the toolbar on the customer's page", async () => {
		const wrapper = mount(CustomerKnowledgeNav, { props, attachTo: pageWithToolbar() })
		await flushPromises()
		expect(wrapper.get('[data-testid="knowledge-nav"]').classes()).not.toContain("in-overlay")
		wrapper.unmount()
	})

	it("is at the top in a modal, outside the toolbar's scroller", async () => {
		pageWithToolbar()
		const wrapper = mount(CustomerKnowledgeNav, { props, attachTo: document.body })
		await flushPromises()
		expect(wrapper.get('[data-testid="knowledge-nav"]').classes()).toContain("in-overlay")
		wrapper.unmount()
	})
})
