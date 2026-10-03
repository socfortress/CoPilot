import { flushPromises, mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { useNavigation } from "@/composables/useNavigation"
import ModalPageButton from "../ModalPageButton.vue"

function router() {
	const blank = { render: () => null }
	return createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/", component: blank },
			{ path: "/customers", name: "Customers", component: blank },
			{ path: "/customers/:code", name: "Customer", component: blank }
		]
	})
}

/** Mounts the button for a customer's page, built the way callers build it. */
async function mountFor(code: string | null, at = "/") {
	const appRouter = router()
	await appRouter.push(at)
	await appRouter.isReady()
	const navigated: string[] = []
	const Host = defineComponent({
		setup() {
			const { routeCustomer } = useNavigation()
			return () =>
				h(ModalPageButton, {
					route: code ? routeCustomer({ code }) : null,
					label: "Open the customer's page",
					onNavigate: () => navigated.push("navigate")
				})
		}
	})
	const wrapper = mount(Host, { global: { plugins: [appRouter] } })
	await flushPromises()
	return { wrapper, appRouter, navigated }
}

describe("modalPageButton", () => {
	it("is a real link to the entity's page, named for screen readers", async () => {
		const { wrapper } = await mountFor("ACME")
		const link = wrapper.get("[data-testid=modal-page-button]")
		expect(link.element.tagName).toBe("A")
		expect(link.attributes("href")).toBe("/customers/ACME")
		expect(link.attributes("aria-label")).toBe("Open the customer's page")
	})

	it("navigates on a plain click and tells the modal to close", async () => {
		const { wrapper, appRouter, navigated } = await mountFor("ACME")
		await wrapper.get("[data-testid=modal-page-button]").trigger("click", { button: 0 })
		await flushPromises()
		expect(navigated).toEqual(["navigate"])
		expect(appRouter.currentRoute.value.fullPath).toBe("/customers/ACME")
	})

	it("leaves a modified click to the browser (new tab), without closing anything", async () => {
		const { wrapper, appRouter, navigated } = await mountFor("ACME")
		await wrapper.get("[data-testid=modal-page-button]").trigger("click", { button: 0, metaKey: true })
		await flushPromises()
		expect(navigated).toEqual([])
		expect(appRouter.currentRoute.value.fullPath).toBe("/")
	})

	it("renders nothing without a page, or on the page it points to", async () => {
		const none = await mountFor(null)
		expect(none.wrapper.find("[data-testid=modal-page-button]").exists()).toBe(false)
		const here = await mountFor("ACME", "/customers/ACME")
		expect(here.wrapper.find("[data-testid=modal-page-button]").exists()).toBe(false)
	})
})
