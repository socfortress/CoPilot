import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import UserCustomersBadge from "../UserCustomersBadge.vue"

/**
 * The users list shows how many customers a user has; hovering the count lists them,
 * each with "View" (a modal of the customer) and "Open" (the customer's page).
 */

const navigate = vi.hoisted(() => vi.fn())

vi.mock("@/composables/useNavigation", () => ({
	useNavigation: () => ({
		routeCustomer: ({ code }: { code: string }) => ({ href: () => `/customers?code=${code}`, navigate })
	})
}))

vi.mock("vue-router", () => ({ useRouter: () => ({ currentRoute: { value: { fullPath: "/users" } } }) }))

// Loaded through defineAsyncComponent, which unwraps `default` only from an ES module.
vi.mock("@/components/customers/CustomerDetails.vue", () => ({
	__esModule: true,
	default: defineComponent({
		props: { customerCode: String },
		setup: props => () => h("div", { "data-testid": "customer-details" }, props.customerCode)
	})
}))

const NAMES = { ACME: "Acme Corp", GLOBEX: "Globex", INITECH: "Initech" }

function render(props: { customerCodes: string[]; roleName?: string; customerNames?: Record<string, string> }) {
	return mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, {
					default: () => h(NDialogProvider, null, { default: () => h(UserCustomersBadge, props) })
				})
		}),
		{ attachTo: document.body }
	)
}

async function hover(wrapper: ReturnType<typeof render>) {
	await wrapper.get("[data-testid=user-customers-count]").trigger("mouseenter")
	await new Promise(resolve => setTimeout(resolve, 250))
	await flushPromises()
}

function inBody(selector: string) {
	return document.body.querySelector<HTMLElement>(selector)
}

beforeEach(() => {
	navigate.mockReset()
	document.body.innerHTML = ""
})

describe("user customers badge", () => {
	it("shows how many customers the user has", () => {
		const wrapper = render({ customerCodes: ["ACME", "GLOBEX"], roleName: "analyst", customerNames: NAMES })
		expect(wrapper.get("[data-testid=user-customers-count]").text()).toBe("2")
	})

	it("says an admin sees every customer instead of counting none", () => {
		const wrapper = render({ customerCodes: [], roleName: "admin", customerNames: NAMES })
		expect(wrapper.find("[data-testid=user-customers-all]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=user-customers-count]").exists()).toBe(false)
	})

	it("lists the customers by name on hover, each with View and Open", async () => {
		const wrapper = render({ customerCodes: ["INITECH", "ACME", "UNKNOWN"], roleName: "responder", customerNames: NAMES })
		await hover(wrapper)

		const list = inBody("[data-testid=user-customers-list]")
		expect(list).not.toBeNull()
		const rows = [...(list?.querySelectorAll("li") ?? [])].map(li => li.querySelector("span")?.textContent)
		// Sorted by name; a code with no known name stands in for it.
		expect(rows).toEqual(["Acme Corp", "Initech", "UNKNOWN"])

		const open = inBody("[data-testid=user-customer-ACME] a")
		expect(open?.getAttribute("href")).toBe("/customers?code=ACME")
		open?.click()
		expect(navigate).toHaveBeenCalledOnce()
	})

	it("opens the customer in a modal from View, which links its page", async () => {
		const wrapper = render({ customerCodes: ["ACME"], roleName: "analyst", customerNames: NAMES })
		await hover(wrapper)

		inBody("[data-testid=user-customer-ACME] button")?.click()
		await vi.dynamicImportSettled()
		await flushPromises()

		expect(inBody("[data-testid=customer-details]")?.textContent).toBe("ACME")
		expect(document.body.querySelector(".n-card-header")?.textContent).toContain("Acme Corp")
		// The modal offers the customer's page next to its close button.
		expect(document.body.querySelector(".n-card-header a")?.getAttribute("href")).toBe("/customers?code=ACME")
	})
})
