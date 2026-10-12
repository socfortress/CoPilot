import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import ProfileCustomers from "../ProfileCustomers.vue"

/** The profile's Customers tab: the signed-in user's customers, from the route that answers for oneself. */

const getMyCustomerAccess = vi.hoisted(() => vi.fn())
const getCustomers = vi.hoisted(() => vi.fn())
const navigate = vi.hoisted(() => vi.fn())

vi.mock("@/api", () => ({
	default: { auth: { getMyCustomerAccess }, customers: { getCustomers } }
}))

vi.mock("@/composables/useNavigation", () => ({
	useNavigation: () => ({
		routeCustomer: (params?: { code?: string }) => ({
			href: () => (params?.code ? `/customers/${params.code}` : "/customers"),
			navigate
		})
	})
}))

vi.mock("vue-router", () => ({ useRouter: () => ({ currentRoute: { value: { fullPath: "/profile" } } }) }))

// Loaded through defineAsyncComponent, which unwraps `default` only from an ES module.
vi.mock("@/components/customers/CustomerDetails.vue", () => ({
	__esModule: true,
	default: defineComponent({
		props: { customerCode: String },
		setup: props => () => h("div", { "data-testid": "customer-details" }, props.customerCode)
	})
}))

function access(scope: string, codes: string[]) {
	getMyCustomerAccess.mockResolvedValue({ data: { success: true, scope, customer_codes: codes } })
}

function render() {
	return mount(ProfileCustomers, { attachTo: document.body })
}

beforeEach(() => {
	getMyCustomerAccess.mockReset()
	navigate.mockReset()
	getCustomers.mockReset().mockResolvedValue({
		data: {
			success: true,
			customers: [
				{ customer_code: "GLOBEX", customer_name: "Globex", customer_type: "MSSP", logo_file: "" },
				{ customer_code: "ACME", customer_name: "Acme Corp", customer_type: "", logo_file: "" }
			]
		}
	})
	document.body.innerHTML = ""
})

function rowNames(wrapper: ReturnType<typeof render>) {
	return wrapper.findAll("[data-testid^=profile-customer-]").map(row => row.get("[data-testid=customer-name]").text())
}

describe("profile customers tab", () => {
	it("lists the assigned customers by name, sorted, with code, type and a count", async () => {
		access("assigned", ["GLOBEX", "ACME", "UNKNOWN"])
		const wrapper = render()
		await flushPromises()

		expect(rowNames(wrapper)).toEqual(["Acme Corp", "Globex", "UNKNOWN"])
		const globex = wrapper.get("[data-testid=profile-customer-GLOBEX]")
		expect(globex.text()).toContain("#GLOBEX")
		expect(globex.text()).toContain("MSSP")
		expect(wrapper.get("[data-testid=profile-customers-count]").text()).toBe("3 customers")
	})

	it("offers each customer's page, and opens it in a modal from View", async () => {
		access("assigned", ["ACME"])
		const wrapper = render()
		await flushPromises()

		const row = wrapper.get("[data-testid=profile-customer-ACME]")
		expect(row.get("a").attributes("href")).toBe("/customers/ACME")

		await row.get("button").trigger("click")
		await vi.dynamicImportSettled()
		await flushPromises()
		expect(document.body.querySelector("[data-testid=customer-details]")?.textContent).toBe("ACME")
		expect(document.body.querySelector(".n-modal .n-card-header")?.textContent).toContain("Acme Corp")
	})

	it("tells an admin they see every customer", async () => {
		access("deployment", ["*"])
		const wrapper = render()
		await flushPromises()

		expect(wrapper.find("[data-testid=profile-customers-all]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=profile-customers-count]").exists()).toBe(false)
		expect(getCustomers).not.toHaveBeenCalled()
	})

	it("warns a user nobody has assigned a customer to", async () => {
		access("unassigned", [])
		const wrapper = render()
		await flushPromises()

		expect(wrapper.find("[data-testid=profile-customers-none]").exists()).toBe(true)
		expect(rowNames(wrapper)).toEqual([])
	})

	it("still lists the codes when the names cannot be loaded", async () => {
		access("assigned", ["ACME"])
		getCustomers.mockRejectedValue(new Error("down"))
		const wrapper = render()
		await flushPromises()

		expect(rowNames(wrapper)).toEqual(["ACME"])
	})

	it("says so when the access cannot be loaded, rather than showing none", async () => {
		getMyCustomerAccess.mockRejectedValue(new Error("down"))
		const wrapper = render()
		await flushPromises()

		expect(wrapper.text()).toContain("could not be loaded")
		expect(wrapper.find("[data-testid=profile-customers-none]").exists()).toBe(false)
	})
})
